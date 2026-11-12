"""Tests for the live pipeline's minute aggregation, state and decisions (no network, no data files).

Run from the repo root: python -m unittest discover -s healthapi/tests -t .
"""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from healthapi import live, probe

T0 = pd.Timestamp("2026-11-12 08:00")


class FakeModel:
    """Stands in for the Random Forest: always confidently stressed."""
    classes_ = np.array(["happy", "neutral", "sad", "stressed"])

    def predict_proba(self, X):
        return np.tile([0.1, 0.1, 0.1, 0.7], (len(X), 1))


ART = {"model": FakeModel(), "features": live.WINDOW_FEATURES, "window_min": 30}


class FakeSource:
    """Heart rate every 5 s, 20 steps a minute, between `worn_from` and `synced_until`."""

    def __init__(self, worn_from, synced_until, fail=False):
        self.worn_from, self.synced_until, self.fail = worn_from, synced_until, fail
        self.calls = []

    def fetch(self, start, end):
        self.calls.append((start, end))
        if self.fail:
            raise RuntimeError("503 on dataPoints")
        lo, hi = max(start, self.worn_from), min(end, self.synced_until)
        times = pd.date_range(lo, hi, freq="5s", inclusive="left")
        hr = pd.DataFrame({"time": times, "bpm": 70 + 10 * np.sin(np.arange(len(times)) / 50)})
        minutes = pd.date_range(lo.ceil("min"), hi, freq="min", inclusive="left")
        steps = pd.DataFrame({"start": minutes, "end": minutes + pd.Timedelta(minutes=1), "steps": 20.0})
        return hr, steps


class Minutes(unittest.TestCase):
    def test_hr_minutes_matches_training_shape(self):
        s = pd.DataFrame({"time": pd.to_datetime(["2026-11-12 08:00:05", "2026-11-12 08:00:35",
                                                  "2026-11-12 08:01:10"]), "bpm": [60.0, 80.0, 75.0]})
        m = live.hr_minutes(s)
        self.assertEqual(list(m.columns), ["minute", "bpm_mean", "bpm_std", "n"])
        self.assertEqual(m["bpm_mean"].tolist(), [70.0, 75.0])
        self.assertEqual(m["bpm_std"].tolist(), [10.0, 0.0])   # population std, like the extraction
        self.assertEqual(m["n"].tolist(), [2, 1])

    def test_steps_spread_over_interval(self):
        iv = pd.DataFrame({"start": [T0], "end": [T0 + pd.Timedelta(minutes=4)], "steps": [400.0]})
        st = live.step_minutes(iv)
        self.assertEqual(len(st), 4)
        self.assertTrue((st == 100).all())
        self.assertEqual(st.sum(), 400)

    def test_short_step_interval_lands_in_its_minute(self):
        iv = pd.DataFrame({"start": [T0 + pd.Timedelta(seconds=10)], "end": [T0 + pd.Timedelta(seconds=40)],
                           "steps": [30.0]})
        st = live.step_minutes(iv)
        self.assertEqual(st.to_dict(), {T0: 30.0})

    def test_later_sync_replaces_a_minute(self):
        old = pd.DataFrame({"minute": [T0, T0 + pd.Timedelta(minutes=1)], "bpm_mean": [60.0, 61.0],
                            "bpm_std": [0.0, 0.0], "n": [1, 1]})
        new = pd.DataFrame({"minute": [T0 + pd.Timedelta(minutes=1)], "bpm_mean": [65.0], "bpm_std": [1.0], "n": [12]})
        m = live.merge_minutes(old, new, "minute")
        self.assertEqual(m["bpm_mean"].tolist(), [60.0, 65.0])


class PipelineTicks(unittest.TestCase):
    def pipe(self, source):
        return live.Pipeline(source, model=ART, baseline_days=1)

    def test_no_data_when_band_not_synced(self):
        src = FakeSource(T0 - pd.Timedelta(hours=6), T0 - pd.Timedelta(minutes=50))
        r = self.pipe(src).tick(T0)
        self.assertEqual(r["reason"], "no_data")
        self.assertEqual(r["lag_min"], 51)   # newest minute is 07:09, the minute before the sync

    def test_confident_persistent_mood_fires_once_then_cooldown(self):
        src = FakeSource(T0 - pd.Timedelta(hours=6), T0 + pd.Timedelta(hours=2))
        pipe = self.pipe(src)
        reasons = [pipe.tick(T0 + pd.Timedelta(minutes=10 * i))["reason"] for i in range(4)]
        self.assertEqual(reasons, ["not_persistent", "intervene", "cooldown", "cooldown"])

    def test_record_fields(self):
        src = FakeSource(T0 - pd.Timedelta(hours=6), T0 + pd.Timedelta(hours=2))
        r = self.pipe(src).tick(T0)
        self.assertEqual(r["predicted"], "stressed")
        self.assertEqual(r["steps_30min"], 600)
        self.assertEqual(r["lag_min"], 0)

    def test_first_tick_reads_baseline_then_only_recent(self):
        src = FakeSource(T0 - pd.Timedelta(hours=6), T0 + pd.Timedelta(hours=2))
        pipe = self.pipe(src)
        pipe.tick(T0)
        pipe.tick(T0 + pd.Timedelta(minutes=10))
        (s1, _), (s2, _) = src.calls
        self.assertEqual(s1, T0 - pd.Timedelta(days=1))
        self.assertEqual(s2, T0 - live.REFETCH)

    def test_fetch_error_is_recorded_not_raised(self):
        r = self.pipe(FakeSource(T0, T0, fail=True)).tick(T0)
        self.assertEqual(r["reason"], "fetch_error")
        self.assertIn("503", r["error"])


class FakeProbe:
    """probe.py's request and parsing helpers, answering with one HR sample and one step interval."""
    body, first_number = staticmethod(probe.body), staticmethod(probe.first_number)   # the real parsers
    interval, sample_time = staticmethod(probe.interval), staticmethod(probe.sample_time)

    def __init__(self):
        self.asked = []

    def points(self, type_id, start, end):
        self.asked.append((type_id, start, end))
        if type_id == "heart-rate":
            return [{"heartRate": {"sampleTime": {"physicalTime": "2026-11-12T13:00:05Z"}, "beatsPerMinute": 72}}]
        return [{"steps": {"interval": {"startTime": "2026-11-12T13:00:00Z", "endTime": "2026-11-12T13:01:00Z"},
                           "count": "15"}}]


class Api(unittest.TestCase):
    def test_times_go_out_as_utc_and_come_back_local(self):
        src = live.ApiSource.__new__(live.ApiSource)
        src.probe = FakeProbe()
        local = pd.Timestamp(datetime(2026, 11, 12, 13, 0, 5, tzinfo=timezone.utc).astimezone()).tz_localize(None)
        hr, steps = src.fetch(local - pd.Timedelta(hours=1), local)
        _, start, end = src.probe.asked[0]
        self.assertEqual(end.utcoffset(), timedelta(0))
        self.assertEqual(end.replace(tzinfo=None), datetime(2026, 11, 12, 13, 0, 5))
        self.assertEqual(hr["time"].tolist(), [local])
        self.assertEqual(hr["bpm"].tolist(), [72.0])
        self.assertEqual(steps["steps"].tolist(), [15.0])


class Log(unittest.TestCase):
    def test_since_filter(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "log.jsonl"
            for t in ("2026-11-12T08:00:00", "2026-11-12T08:10:00"):
                live.append_log({"time": t, "reason": "no_data"}, path)
            self.assertEqual(len(live.read_log(path)), 2)
            self.assertEqual([r["time"] for r in live.read_log(path, since="2026-11-12T08:00:00")],
                             ["2026-11-12T08:10:00"])


if __name__ == "__main__":
    unittest.main()
