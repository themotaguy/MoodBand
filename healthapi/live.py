"""Live pipeline skeleton: Fitbit data -> 30-min window -> Random Forest -> decision module.

The four stages of the architecture (sense -> process -> classify -> feedback
decision), run on the laptop. Every `--every` minutes it:
  1. fetches new heart-rate and step data from a source,
  2. turns it into per-minute series, the same shape as the LifeSnaps training data
     (bpm_mean / bpm_std / n per minute, steps per minute),
  3. builds the model's 12 window features for the 30 minutes ending now
     (model/windows.py; hr_rel and hr_z use the person's own baseline from the
     last `--baseline-days` days, the "personal body baselines" of decisions.md #20),
  4. runs the saved Random Forest (model/artifacts/rf_baseline.joblib),
  5. passes the probabilities to FeedbackDecider, and
  6. appends the result to data/live/log.jsonl, which feedback/server.py serves to
     the phone at GET /live.

Sources:
  api       the Google Health API (healthapi/probe.py's sign-in and requests).
            Field names are unconfirmed until `probe.py raw` runs on real data.
  recorded  one LifeSnaps participant-day on a simulated clock (08:00-22:00), to
            test the plumbing before the band is paired. The saved model was
            trained on every LifeSnaps participant, so these predictions are not
            an evaluation (replay mode uses held-out predictions for that).

Only physiological and motion data are inputs; the person's answers never are
(decisions.md #20).

Usage (from the repo root):
  .venv/bin/python -m healthapi.live --source recorded [--id <participant>] [--date YYYY-MM-DD]
  .venv/bin/python -m healthapi.live --source api [--every 10] [--once]
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))
sys.path.insert(0, str(ROOT))

from feedback.decision import Config, FeedbackDecider, Prediction, UserSettings  # noqa: E402
from windows import WINDOW_FEATURES, window_features  # noqa: E402

MODEL_PATH = ROOT / "model" / "artifacts" / "rf_baseline.joblib"
LOG = ROOT / "data" / "live" / "log.jsonl"
ME = "me"
REFETCH = timedelta(hours=2)   # re-read this far back each tick: data arrives late, after a sync


# ---------- samples -> minutes ----------

def hr_minutes(samples):
    """Heart-rate samples (time, bpm) -> per-minute bpm_mean, bpm_std, n, like the LifeSnaps extraction."""
    if samples.empty:
        return pd.DataFrame(columns=["minute", "bpm_mean", "bpm_std", "n"])
    g = samples.assign(minute=samples["time"].dt.floor("min")).groupby("minute")["bpm"]
    out = pd.DataFrame({"bpm_mean": g.mean(), "bpm_std": g.std(ddof=0), "n": g.size()})
    return out.reset_index()


def step_minutes(intervals):
    """Step intervals (start, end, steps) -> steps per minute, each interval spread evenly over its minutes."""
    per_minute = {}
    for r in intervals.itertuples(index=False):
        first, last = r.start.floor("min"), (r.end - pd.Timedelta(seconds=1)).floor("min")
        minutes = pd.date_range(first, max(first, last), freq="min")
        for m in minutes:
            per_minute[m] = per_minute.get(m, 0.0) + r.steps / len(minutes)
    return pd.Series(per_minute, dtype=float).sort_index()


def merge_minutes(old, new, key):
    """New minutes replace old ones (a later sync can fill in a minute)."""
    if old is None or len(old) == 0:
        return new
    if key is None:   # steps Series indexed by minute
        return pd.concat([old[~old.index.isin(new.index)], new]).sort_index()
    return pd.concat([old[~old[key].isin(new[key])], new]).sort_values(key).reset_index(drop=True)


# ---------- sources ----------

class ApiSource:
    """Google Health API. Times come back in UTC; the model uses local clock time (hour_sin/cos)."""

    def __init__(self):
        from healthapi import probe
        self.probe = probe

    @staticmethod
    def _local(t):
        return pd.Timestamp(t.astimezone()).tz_localize(None)

    def fetch(self, start, end):
        p = self.probe
        utc = lambda t: t.astimezone(timezone.utc)  # noqa: E731
        hr = []
        for dp in p.points("heart-rate", utc(start), utc(end)):
            b = p.body(dp, "heart-rate")
            t, bpm = p.sample_time(b), p.first_number(b, ["beatsPerMinute"])
            if t and bpm:
                hr.append((self._local(t), bpm))
        steps = []
        for dp in p.points("steps", utc(start), utc(end)):
            b = p.body(dp, "steps")
            (a, z), n = p.interval(b), p.first_number(b, ["count", "steps"])
            if a and z and n is not None:
                steps.append((self._local(a), self._local(z), n))
        return (pd.DataFrame(hr, columns=["time", "bpm"]),
                pd.DataFrame(steps, columns=["start", "end", "steps"]))


class RecordedSource:
    """One LifeSnaps participant's minute files, served as if they were arriving live."""

    def __init__(self, pid):
        from windows import load_minutes
        hr_by_id, steps_by_id = load_minutes()
        if pid not in hr_by_id:
            raise SystemExit(f"No heart rate for participant {pid}.")
        self.hr = hr_by_id[pid]
        self.steps = steps_by_id.get(pid, pd.Series(dtype=float))

    def fetch(self, start, end):
        hr = self.hr[(self.hr["minute"] >= start) & (self.hr["minute"] < end)]
        st = self.steps[(self.steps.index >= start) & (self.steps.index < end)]
        # Already per minute: present each minute as one sample / one 1-minute interval.
        samples = pd.DataFrame({"time": hr["minute"], "bpm": hr["bpm_mean"]})
        intervals = pd.DataFrame({"start": st.index, "end": st.index + pd.Timedelta(minutes=1), "steps": st.values})
        return samples, intervals


# ---------- pipeline ----------

class Pipeline:
    def __init__(self, source, model=None, config=Config(), user=None, baseline_days=14):
        art = model or joblib.load(MODEL_PATH)
        self.model, self.features, self.window_min = art["model"], art["features"], art["window_min"]
        self.source, self.user = source, user or UserSettings()
        self.decider = FeedbackDecider(config)
        self.baseline = pd.Timedelta(days=baseline_days)
        self.hr, self.steps, self.fetched_until = None, None, None

    def _update(self, now):
        start = now - self.baseline if self.fetched_until is None else self.fetched_until - REFETCH
        samples, intervals = self.source.fetch(start, now)
        self.hr = merge_minutes(self.hr, hr_minutes(samples), "minute")
        self.steps = merge_minutes(self.steps, step_minutes(intervals), None)
        keep = now - self.baseline
        self.hr = self.hr[self.hr["minute"] >= keep].reset_index(drop=True)
        self.steps = self.steps[self.steps.index >= keep]
        self.fetched_until = now

    def tick(self, now):
        """One decision point. Returns a JSON-ready record."""
        now = pd.Timestamp(now).floor("min")
        try:
            self._update(now)
        except (RuntimeError, OSError) as e:   # network or API error: skip this tick, keep the state
            return {"time": now.isoformat(), "reason": "fetch_error", "error": str(e)[:300]}
        latest = self.hr["minute"].max() if len(self.hr) else None
        record = {"time": now.isoformat(),
                  "latest_hr": latest.isoformat() if latest is not None else None,
                  "lag_min": round((now - latest).total_seconds() / 60) if latest is not None else None}
        w = window_features(pd.DataFrame({"id": [ME], "ts": [now]}), {ME: self.hr}, {ME: self.steps},
                            self.window_min)
        if w.empty:
            # Under 50% of the last 30 minutes have heart rate (not worn, or not synced yet).
            return {**record, "reason": "no_data"}
        proba = dict(zip(self.model.classes_, self.model.predict_proba(w[self.features])[0]))
        probabilities = {m: round(float(p), 3) for m, p in proba.items()}
        steps = int(w["steps_sum"].iloc[0])
        d = self.decider.decide(Prediction(now.to_pydatetime(), probabilities, steps), self.user)
        return {**record,
                "probabilities": probabilities,
                "predicted": max(probabilities, key=probabilities.get),
                "steps_30min": steps,
                "hr_mean": round(float(w["hr_mean"].iloc[0]), 1),
                "reason": d.reason,
                "mood": d.mood,
                "intervention": d.intervention["id"] if d.acts else None}


def append_log(record, path=LOG):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def read_log(path=LOG, since=None):
    """Records after `since` (ISO time), oldest first."""
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [r for r in rows if since is None or r["time"] > since]


def show(r):
    if r["reason"] in ("no_data", "fetch_error"):
        print(f"{r['time'][11:16]}  {r['reason']}" + (f"  (latest HR {r['lag_min']} min ago)" if r.get("lag_min") is not None else
                                                      f"  {r.get('error', '')}"), flush=True)
        return
    p = "  ".join(f"{m} {v:.2f}" for m, v in r["probabilities"].items())
    fired = f"  -> {r['intervention']}" if r["intervention"] else ""
    print(f"{r['time'][11:16]}  HR {r['hr_mean']:5.1f}  steps {r['steps_30min']:5d}  {p}  "
          f"{r['reason']}{fired}", flush=True)


def pick_day(pid=None, date=None):
    """A participant-day with plenty of heart rate (default: the first replay demo day)."""
    if pid and date:
        return pid, date
    from feedback import replay
    preds, reports = replay.load()
    day = replay.demo_days(preds, reports, limit=1)[0]
    return pid or day["id"], date or day["date"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source", choices=["api", "recorded"], required=True)
    ap.add_argument("--every", type=int, default=10, help="minutes between decision points")
    ap.add_argument("--once", action="store_true", help="api: run a single tick and stop")
    ap.add_argument("--baseline-days", type=int, default=14)
    ap.add_argument("--id"), ap.add_argument("--date")
    ap.add_argument("--profile", choices=["sighted", "low_vision", "blind"], default="sighted")
    args = ap.parse_args()
    user = UserSettings(profile=args.profile)

    if args.source == "recorded":
        pid, date = pick_day(args.id, args.date)
        print(f"Recorded day: participant {pid[-4:]}, {date} (simulated clock; log not written)\n")
        pipe = Pipeline(RecordedSource(pid), user=user, baseline_days=args.baseline_days)
        day = pd.Timestamp(date)
        for now in pd.date_range(day + pd.Timedelta(hours=8), day + pd.Timedelta(hours=22),
                                 freq=f"{args.every}min", inclusive="left"):
            show(pipe.tick(now))
        return

    pipe = Pipeline(ApiSource(), user=user, baseline_days=args.baseline_days)
    print(f"Live: a decision every {args.every} min; log at {LOG.relative_to(ROOT)}\n", flush=True)
    while True:
        r = pipe.tick(datetime.now())
        append_log(r)
        show(r)
        if args.once:
            return
        time.sleep(args.every * 60)


if __name__ == "__main__":
    main()
