"""Tests for replay mode's timeline, demo-day ranking and answer saving.

Run from the repo root: python -m unittest discover -s feedback/tests -t .
"""

import csv
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from feedback import replay
from feedback.server import save_answer

PID, DAY = "p1", "2022-01-05"


def predictions(moods, pid=PID, day=DAY, steps=0):
    """One 10-minute prediction from 08:00 per mood (None = unconfident)."""
    rows = []
    for i, mood in enumerate(moods):
        p = {"happy": 0.3, "neutral": 0.3, "sad": 0.2, "stressed": 0.2} if mood is None else \
            {m: 0.7 if m == mood else 0.1 for m in replay.MOODS}
        rows.append({"id": pid, "ts": pd.Timestamp(f"{day} 08:00") + pd.Timedelta(minutes=10 * i),
                     "steps_sum": steps, **p})
    return pd.DataFrame(rows)


def reports(*items, pid=PID, day=DAY):
    rows = [{"id": pid, "ts": pd.Timestamp(f"{day} {t}"), "mood": m} for t, m in items]
    return pd.DataFrame(rows, columns=["id", "ts", "mood"]).astype({"ts": "datetime64[ns]"})


class TimelineTest(unittest.TestCase):
    def test_persistent_stress_fires_breathing_with_nearby_report(self):
        t = replay.timeline(predictions(["stressed", "stressed", None]), reports(("08:15", "stressed")), PID, DAY)
        fired = [s for s in t["steps"] if s["intervention"]]
        self.assertEqual([(s["time"], s["intervention"], s["reported"]) for s in fired],
                         [("08:10", "breathing_break", "stressed")])
        self.assertEqual(t["steps"][1]["minute"], 8 * 60 + 10)
        self.assertEqual(t["reports"], [{"time": "08:15", "minute": 495, "mood": "stressed"}])

    def test_steps_without_a_decision_have_no_report(self):
        t = replay.timeline(predictions(["stressed", None]), reports(("08:00", "stressed")), PID, DAY)
        self.assertEqual([s["reason"] for s in t["steps"]], ["not_persistent", "low_confidence"])
        self.assertTrue(all(s["reported"] is None for s in t["steps"]))

    def test_exercise_blocks_stress(self):
        t = replay.timeline(predictions(["stressed"] * 3, steps=2000), reports(), PID, DAY)
        self.assertEqual({s["reason"] for s in t["steps"]}, {"exercise"})

    def test_unknown_day(self):
        with self.assertRaises(KeyError):
            replay.timeline(predictions(["happy"]), reports(), PID, "2022-02-01")


class DemoDaysTest(unittest.TestCase):
    def test_matched_days_rank_first_and_quiet_days_are_dropped(self):
        preds = pd.concat([
            predictions(["sad", "sad"], pid="miss"),
            predictions(["stressed", "stressed"], pid="hit"),
            predictions(["happy", "happy"], pid="quiet"),
        ])
        reps = pd.concat([reports(("08:10", "stressed"), pid="hit"), reports(("08:10", "happy"), pid="miss")])
        days = replay.demo_days(preds, reps)
        self.assertEqual([(d["id"], d["matched"]) for d in days], [("hit", 1), ("miss", 0)])


class SaveAnswerTest(unittest.TestCase):
    def answer(self, **changes):
        return {"answered_at": "2026-10-22T10:00:00", "id": PID, "date": DAY, "time": "08:10",
                "intervention": "breathing_break", "predicted_mood": "stressed",
                "answer": "yes", "profile": "blind", **changes}

    def test_appends_with_reported_mood(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "answers.csv"
            save_answer(self.answer(), reports(("08:20", "stressed")), path)
            save_answer(self.answer(answer="no"), reports(), path)
            with open(path) as f:
                rows = list(csv.DictReader(f))
        self.assertEqual([(r["answer"], r["reported_mood"]) for r in rows], [("yes", "stressed"), ("no", "")])

    def test_rejects_bad_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "answers.csv"
            for bad in (self.answer(answer="maybe"), self.answer(profile="x"), self.answer(id="")):
                with self.assertRaises(ValueError):
                    save_answer(bad, reports(), path)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
