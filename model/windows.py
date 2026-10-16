"""Features from the minutes right before each mood report.

Built from the minute-level files written by extract_lifesnaps_mongo.py. Unlike
the hourly CSV (whole-hour averages, report hour only), each SEMA3 response gets
heart-rate and step features from the `window_min` minutes ending at its exact
completion time. This mirrors deployment: at any moment, the app classifies
from the user's last N minutes of Fitbit data.

Feature policy as in lifesnaps.py: real-time HR + motion only (decisions.md §3, #8).
"""

import numpy as np
import pandas as pd

from lifesnaps import REPO_ROOT, SEMA_TO_MOODBAND

DATA = REPO_ROOT / "data" / "lifesnaps"
MIN_COVERAGE = 0.5  # require HR in at least half the window's minutes

WINDOW_FEATURES = [
    "hr_mean", "hr_std", "hr_min", "hr_max", "hr_slope", "hr_within_std",
    "hr_rel", "hr_z", "steps_sum", "active_min", "hour_sin", "hour_cos",
]


def load_minutes():
    """Per-participant minute series: {id: (minutes, bpm_mean, bpm_std)}, {id: steps Series}."""
    for name in ("sema_responses.csv", "minute_hr.csv.gz", "minute_steps.csv.gz"):
        if not (DATA / name).exists():
            raise FileNotFoundError(f"{DATA / name} missing — run model/extract_lifesnaps_mongo.py first.")
    hr = pd.read_csv(DATA / "minute_hr.csv.gz")
    hr["minute"] = pd.to_datetime(hr["minute"])
    steps = pd.read_csv(DATA / "minute_steps.csv.gz")
    steps["minute"] = pd.to_datetime(steps["minute"])
    hr_by_id = {pid: g.sort_values("minute") for pid, g in hr.groupby("id")}
    steps_by_id = {pid: g.set_index("minute")["steps"].sort_index() for pid, g in steps.groupby("id")}
    return hr_by_id, steps_by_id


def window_dataset(window_min=30, minutes=None):
    """(X, y, groups, df) — one row per mapped SEMA3 response with enough HR coverage."""
    hr_by_id, steps_by_id = minutes or load_minutes()
    sema = pd.read_csv(DATA / "sema_responses.csv")
    sema["mood"] = sema["mood"].map(SEMA_TO_MOODBAND)
    sema = sema.dropna(subset=["mood"])
    sema["ts"] = pd.to_datetime(sema["completed_ts"]).dt.floor("min")

    window = pd.Timedelta(minutes=window_min)
    rows = []
    for r in sema.itertuples():
        hr = hr_by_id.get(r.id)
        if hr is None:
            continue
        person_mean, person_std = hr["bpm_mean"].mean(), hr["bpm_mean"].std()
        lo, hi = hr["minute"].searchsorted([r.ts - window, r.ts], side="right")
        w = hr.iloc[lo:hi]
        if len(w) < MIN_COVERAGE * window_min:
            continue
        t = (w["minute"] - r.ts).dt.total_seconds().to_numpy() / 60
        st = steps_by_id.get(r.id, pd.Series(dtype=float))
        st = st[(st.index > r.ts - window) & (st.index <= r.ts)]
        hr_mean = w["bpm_mean"].mean()
        rows.append({
            "id": r.id, "ts": r.ts, "mood": r.mood,
            "hr_mean": hr_mean,
            "hr_std": w["bpm_mean"].std(),
            "hr_min": w["bpm_mean"].min(),
            "hr_max": w["bpm_mean"].max(),
            "hr_slope": np.polyfit(t, w["bpm_mean"], 1)[0],
            "hr_within_std": w["bpm_std"].mean(),
            "hr_rel": hr_mean - person_mean,
            "hr_z": (hr_mean - person_mean) / person_std,
            "steps_sum": st.sum(),
            "active_min": int((st > 0).sum()),
            "hour_sin": np.sin(2 * np.pi * r.ts.hour / 24),
            "hour_cos": np.cos(2 * np.pi * r.ts.hour / 24),
        })
    df = pd.DataFrame(rows)
    return df[WINDOW_FEATURES], df["mood"], df["id"], df
