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


def load_minutes(data_dir=DATA):
    """Per-participant minute series: {id: DataFrame(minute, bpm_mean, bpm_std, n)}, {id: steps Series}."""
    for name in ("minute_hr.csv.gz", "minute_steps.csv.gz"):
        if not (data_dir / name).exists():
            raise FileNotFoundError(f"{data_dir / name} missing — run the dataset's extraction script first.")
    hr = pd.read_csv(data_dir / "minute_hr.csv.gz")
    hr["minute"] = pd.to_datetime(hr["minute"])
    steps = pd.read_csv(data_dir / "minute_steps.csv.gz")
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
    df = window_features(sema[["id", "ts", "mood"]], hr_by_id, steps_by_id, window_min)
    return df[WINDOW_FEATURES], df["mood"], df["id"], df


def window_features(reports, hr_by_id, steps_by_id, window_min=30):
    """Features from the window_min minutes ending at each report.

    reports: DataFrame with id and ts (local time, minute precision); any other
    columns (labels) are carried through. Reports with < MIN_COVERAGE HR minutes
    in the window are dropped. Shared by LifeSnaps and PMData (pmdata.py).
    """
    window = pd.Timedelta(minutes=window_min)
    rows = []
    for r in reports.to_dict("records"):
        hr = hr_by_id.get(r["id"])
        if hr is None:
            continue
        ts = r["ts"]
        person_mean, person_std = hr["bpm_mean"].mean(), hr["bpm_mean"].std()
        lo, hi = hr["minute"].searchsorted([ts - window, ts], side="right")
        w = hr.iloc[lo:hi]
        if len(w) < MIN_COVERAGE * window_min:
            continue
        t = (w["minute"] - ts).dt.total_seconds().to_numpy() / 60
        st = steps_by_id.get(r["id"], pd.Series(dtype=float))
        st = st[(st.index > ts - window) & (st.index <= ts)]
        hr_mean = w["bpm_mean"].mean()
        rows.append({
            **r,
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
            "hour_sin": np.sin(2 * np.pi * ts.hour / 24),
            "hour_cos": np.cos(2 * np.pi * ts.hour / 24),
        })
    return pd.DataFrame(rows)
