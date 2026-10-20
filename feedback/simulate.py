"""Replay held-out LifeSnaps predictions through the feedback-decision module.

In deployment the classifier runs continuously, not only when someone reports a
mood. So for each day on which a participant made at least one mood report, this
script predicts every 10 minutes from 08:00 to 22:00 using a model that never saw
that participant (participant-grouped 5-fold CV), then replays those predictions
through FeedbackDecider. For each confidence threshold it reports:
  * burden    — interventions per person-day, and the share of days with any
  * precision — of interventions that fired within 30 min of a real mood report,
                how often the reported mood matched (vs. chance = that mood's share
                of all reports)
  * recall    — of stressed/sad reports, how often the matching intervention fired
                within 30 min
This picks the default min_confidence (Docs/feedback-module-plan.md).

Predictions are cached in data/lifesnaps/sim_predictions.csv.gz (delete to rebuild).

Usage: python feedback/simulate.py
"""

import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))
sys.path.insert(0, str(ROOT))

from feedback.decision import Config, FeedbackDecider, Prediction, UserSettings  # noqa: E402
from train_baseline import SEED, WINDOW_MIN, make_rf  # noqa: E402
from windows import DATA, WINDOW_FEATURES, load_minutes, window_dataset, window_features  # noqa: E402

CACHE = DATA / "sim_predictions.csv.gz"
STEP_MIN = 10
DAY_START, DAY_END = 8, 22
MATCH = timedelta(minutes=30)
THRESHOLDS = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]


def build_predictions():
    minutes = load_minutes()
    X, y, groups, reports = window_dataset(WINDOW_MIN, minutes)
    days = reports.assign(date=reports["ts"].dt.normalize())[["id", "date"]].drop_duplicates()
    offsets = pd.timedelta_range(f"{DAY_START}h", f"{DAY_END}h", freq=f"{STEP_MIN}min", closed="left")
    grid = days.merge(pd.DataFrame({"offset": offsets}), how="cross")
    grid["ts"] = grid["date"] + grid["offset"]
    print(f"{len(days):,} report days -> {len(grid):,} candidate prediction times", flush=True)

    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    parts = []
    for fold, (train, test) in enumerate(cv.split(X, y, groups), 1):
        model = make_rf().fit(X.iloc[train], y.iloc[train])
        test_ids = set(groups.iloc[test])
        windows = window_features(grid.loc[grid["id"].isin(test_ids), ["id", "ts"]], *minutes, WINDOW_MIN)
        proba = pd.DataFrame(model.predict_proba(windows[WINDOW_FEATURES]),
                             columns=model.classes_, index=windows.index)
        parts.append(pd.concat([windows[["id", "ts", "steps_sum"]], proba], axis=1))
        print(f"  fold {fold}: {len(windows):,} predictions", flush=True)
    preds = pd.concat(parts, ignore_index=True)
    preds.to_csv(CACHE, index=False)
    return preds


def replay(preds, config):
    moods = [c for c in preds.columns if c not in ("id", "ts", "steps_sum")]
    fired = []
    for pid, g in preds.groupby("id"):
        decider = FeedbackDecider(config)
        for row in g.sort_values("ts").itertuples(index=False):
            p = Prediction(row.ts.to_pydatetime(), {m: getattr(row, m) for m in moods}, int(row.steps_sum))
            d = decider.decide(p, UserSettings())
            if d.acts:
                fired.append((pid, row.ts, d.reason, d.mood))
    return pd.DataFrame(fired, columns=["id", "ts", "reason", "mood"])


def score(fired, preds, reports):
    person_days = preds.assign(date=preds["ts"].dt.date)[["id", "date"]].drop_duplicates()
    negative = fired[fired["reason"] == "intervene"]
    per_day = negative.assign(date=negative["ts"].dt.date).groupby(["id", "date"]).size()
    row = {
        "per_day": per_day.sum() / len(person_days),
        "days_with_any": len(per_day) / len(person_days),
        "recovery_per_day": (fired["reason"] == "recovery").sum() / len(person_days),
    }
    for mood in ("stressed", "sad"):
        hits = matched = 0
        for f in negative[negative["mood"] == mood].itertuples():
            near = reports[(reports["id"] == f.id) & ((reports["ts"] - f.ts).abs() <= MATCH)]
            if len(near):
                matched += 1
                hits += (near["mood"] == mood).any()
        target = reports[reports["mood"] == mood]
        caught = sum(((negative["id"] == r.id) & (negative["mood"] == mood)
                      & ((negative["ts"] - r.ts).abs() <= MATCH)).any() for r in target.itertuples())
        row[f"{mood}_precision"] = hits / matched if matched else np.nan
        row[f"{mood}_matched"] = matched
        row[f"{mood}_recall"] = caught / len(target)
    return row


def main():
    if CACHE.exists():
        preds = pd.read_csv(CACHE, parse_dates=["ts"])
        print(f"Loaded {len(preds):,} cached predictions from {CACHE}")
    else:
        preds = build_predictions()
    _, _, _, reports = window_dataset(WINDOW_MIN)
    reports = reports[["id", "ts", "mood"]]
    chance = reports["mood"].value_counts(normalize=True)
    print(f"Chance precision (share of reports): stressed {chance['stressed']:.2f}, sad {chance['sad']:.2f}")
    top = preds[["happy", "neutral", "sad", "stressed"]].max(axis=1)
    print(f"Top-class probability across predictions: median {top.median():.2f}, "
          f"90th pct {top.quantile(0.9):.2f}, max {top.max():.2f}\n")

    rows = []
    for threshold in THRESHOLDS:
        fired = replay(preds, Config(min_confidence=threshold))
        rows.append({"min_confidence": threshold, **score(fired, preds, reports)})
    table = pd.DataFrame(rows).set_index("min_confidence")
    pd.set_option("display.width", 200)
    print(table.round(3).to_string())


if __name__ == "__main__":
    main()
