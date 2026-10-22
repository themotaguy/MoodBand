"""Replay mode: one recorded LifeSnaps day through the model and the decision module.

Before the live Fitbit, the app is driven by recorded data (decisions.md #18). For a
participant-day, every 10-minute prediction from 08:00 to 22:00 comes from a Random
Forest that never saw that participant (simulate.py's cached predictions); each is
fed to FeedbackDecider, and the result is a timeline the app plays back in
compressed time: probabilities, the decision and its reason, the intervention when
one fires, and the person's own mood reports for comparison.

The decisions don't depend on the accessibility profile (only the channels do), so
the app resolves channels itself from the shared catalog.
"""

from datetime import timedelta

import pandas as pd

from feedback.decision import Config, FeedbackDecider, Prediction, UserSettings

MATCH = timedelta(minutes=30)   # same window simulate.py uses to match a report
MOODS = ["happy", "neutral", "sad", "stressed"]


def load():
    """Cached held-out predictions and the labelled mood reports (needs data/lifesnaps/)."""
    from feedback.simulate import CACHES, WINDOW_MIN, build_predictions, window_dataset
    cache = CACHES["rf"]
    preds = pd.read_csv(cache, parse_dates=["ts"]) if cache.exists() else build_predictions("rf")
    _, _, _, reports = window_dataset(WINDOW_MIN)
    return preds, reports[["id", "ts", "mood"]]


def _day(df, pid, date):
    return df[(df["id"] == pid) & (df["ts"].dt.normalize() == pd.Timestamp(date))].sort_values("ts")


def nearest_report(reports, pid, ts):
    """Mood the person reported within 30 min of `ts`, or None."""
    near = reports[(reports["id"] == pid) & ((reports["ts"] - ts).abs() <= MATCH)]
    if near.empty:
        return None
    return near.loc[(near["ts"] - ts).abs().idxmin(), "mood"]


def timeline(preds, reports, pid, date, config=Config()):
    day = _day(preds, pid, date)
    if day.empty:
        raise KeyError(f"no predictions for {pid} on {date}")
    decider, user = FeedbackDecider(config), UserSettings()
    start = day["ts"].iloc[0].normalize()
    steps = []
    for row in day.itertuples(index=False):
        probabilities = {m: round(float(getattr(row, m)), 3) for m in MOODS}
        d = decider.decide(Prediction(row.ts.to_pydatetime(), probabilities, int(row.steps_sum)), user)
        steps.append({
            "time": row.ts.strftime("%H:%M"),
            "minute": int((row.ts - start).total_seconds() // 60),
            "probabilities": probabilities,
            "predicted": max(probabilities, key=probabilities.get),
            "reason": d.reason,
            "mood": d.mood,
            "intervention": d.intervention["id"] if d.acts else None,
            "reported": nearest_report(reports, pid, row.ts) if d.acts else None,
        })
    own = _day(reports, pid, date)
    return {
        "id": pid,
        "date": str(pd.Timestamp(date).date()),
        "steps": steps,
        "reports": [{"time": t.strftime("%H:%M"), "minute": int((t - start).total_seconds() // 60), "mood": m}
                    for t, m in zip(own["ts"], own["mood"])],
    }


def demo_days(preds, reports, config=Config(), limit=20):
    """Days worth demoing: most suggestions that matched a real report, then most suggestions."""
    rows = []
    for (pid, date), _ in preds.groupby(["id", preds["ts"].dt.normalize()]):
        t = timeline(preds, reports, pid, date, config)
        fired = [s for s in t["steps"] if s["intervention"]]
        rows.append({
            "id": pid,
            "date": t["date"],
            "suggestions": len(fired),
            "matched": sum(s["reported"] == s["mood"] for s in fired),
            "reports": len(t["reports"]),
        })
    days = pd.DataFrame(rows)
    days = days[days["suggestions"] > 0].sort_values(["matched", "suggestions", "reports"], ascending=False)
    return days.head(limit).to_dict("records")
