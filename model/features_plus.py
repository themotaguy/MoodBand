"""Extra feature groups for the feature experiment (feature_experiment.py).

Each group uses only data the Google Health API exposes (or that the app could
ask once at sign-up), and only data available at the moment of the report:

  B  heart rate unexplained by activity, longer context, weekday/weekend
  C  calories (Fitbit's activity-energy estimate) and exercise sessions
  D  last night's physiology as deviations from the person's own normal
  E  sign-up profile: age band, gender, BMI, first STAI score, Big Five traits

Per-person statistics (baselines, typical heart rate per activity level) use
that person's own unlabelled data, as a calibration period would in the app.
"""

import numpy as np
import pandas as pd

from lifesnaps import DEFAULT_DAILY_CSV, load_hourly
from windows import DATA

STEP_BINS = [-1, 0, 50, 200, 500, 1000, np.inf]  # steps in the previous 10 minutes

GROUP_B = ["resid_mean", "resid_max", "hr_rel_2h", "hr_rel_6h", "steps_2h", "hr_trend", "is_weekend"]
GROUP_C = ["cal_rel_30", "cal_rel_2h", "exercise_min_60", "min_since_exercise", "exercises_today"]
OVERNIGHT = ["rmssd", "nremhr", "spo2", "nightly_temperature", "sleep_duration",
             "sleep_efficiency", "sleep_deep_ratio", "sleep_rem_ratio"]
GROUP_D = [f"{c}_z" for c in OVERNIGHT] + ["resting_hr_prev_z"]
GROUP_E = ["age_30plus", "female", "bmi", "stai_first",
           "extraversion", "agreeableness", "conscientiousness", "stability", "intellect"]


def _minutes(name, value):
    df = pd.read_csv(DATA / name)
    df["minute"] = pd.to_datetime(df["minute"])
    return {pid: g.set_index("minute")[value].sort_index() for pid, g in df.groupby("id")}


def _person_tables(hr_by_id, steps_by_id):
    """Per person: bpm and its residual vs. the person's typical HR at that activity level."""
    out = {}
    for pid, hr in hr_by_id.items():
        bpm = hr.set_index("minute")["bpm_mean"]
        steps = steps_by_id.get(pid, pd.Series(dtype=float))
        lo = min(bpm.index.min(), steps.index.min() if len(steps) else bpm.index.min())
        hi = max(bpm.index.max(), steps.index.max() if len(steps) else bpm.index.max())
        grid = steps.reindex(pd.date_range(lo, hi, freq="min"), fill_value=0).astype(float)
        steps10 = grid.rolling(10, min_periods=1).sum().reindex(bpm.index)
        level = pd.cut(steps10, STEP_BINS, labels=False)
        expected = bpm.groupby(level).median()
        resid = bpm - level.map(expected)
        out[pid] = {"bpm": bpm, "resid": resid, "steps_grid": grid, "mean": bpm.mean()}
    return out


def _window(series, ts, minutes, end_offset=0):
    """Values in (ts - minutes, ts - end_offset], series indexed by sorted minute."""
    lo, hi = series.index.searchsorted([ts - pd.Timedelta(minutes=minutes), ts - pd.Timedelta(minutes=end_offset)], side="right")
    return series.iloc[lo:hi]


def add_group_b(df, tables):
    rows = []
    for r in df[["id", "ts"]].itertuples(index=False):
        t = tables[r.id]
        res30, bpm30 = _window(t["resid"], r.ts, 30), _window(t["bpm"], r.ts, 30)
        bpm2h, bpm6h = _window(t["bpm"], r.ts, 120), _window(t["bpm"], r.ts, 360)
        earlier = _window(t["bpm"], r.ts, 120, end_offset=30)
        rows.append({
            "resid_mean": res30.mean(), "resid_max": res30.max(),
            "hr_rel_2h": bpm2h.mean() - t["mean"], "hr_rel_6h": bpm6h.mean() - t["mean"],
            "steps_2h": _window(t["steps_grid"], r.ts, 120).sum(),
            "hr_trend": bpm30.mean() - earlier.mean() if len(earlier) else np.nan,
            "is_weekend": int(r.ts.dayofweek >= 5),
        })
    return df.join(pd.DataFrame(rows, index=df.index))


def add_group_c(df):
    cal = _minutes("minute_calories.csv.gz", "calories")
    ex = pd.read_csv(DATA / "exercises.csv", parse_dates=["start"])
    ex["end"] = ex["start"] + pd.to_timedelta(ex["minutes"], unit="min")
    ex_by_id = {pid: g.sort_values("start") for pid, g in ex.groupby("id")}
    rows = []
    for r in df[["id", "ts"]].itertuples(index=False):
        c = cal.get(r.id)
        base = c.mean() if c is not None else np.nan
        row = {"cal_rel_30": (_window(c, r.ts, 30).mean() - base) if c is not None else np.nan,
               "cal_rel_2h": (_window(c, r.ts, 120).mean() - base) if c is not None else np.nan}
        e = ex_by_id.get(r.id)
        if e is None:
            row.update(exercise_min_60=0.0, min_since_exercise=1440.0, exercises_today=0)
        else:
            past = e[e["start"] <= r.ts]
            hour_ago = r.ts - pd.Timedelta(minutes=60)
            overlap = (past["end"].clip(upper=r.ts) - past["start"].clip(lower=hour_ago)).dt.total_seconds() / 60
            ended = past[past["end"] <= r.ts]
            row.update(
                exercise_min_60=float(overlap.clip(lower=0).sum()),
                min_since_exercise=float(min(1440, (r.ts - ended["end"].max()).total_seconds() / 60)) if len(ended) else 1440.0,
                exercises_today=int((past["start"].dt.normalize() == r.ts.normalize()).sum()),
            )
        rows.append(row)
    return df.join(pd.DataFrame(rows, index=df.index))


def add_group_d(df):
    daily = load_hourly(DEFAULT_DAILY_CSV)[["id", "date", "resting_hr"] + OVERNIGHT].copy()
    daily["date"] = pd.to_datetime(daily["date"])
    for c in ["resting_hr"] + OVERNIGHT:
        daily[c] = pd.to_numeric(daily[c], errors="coerce")
    daily[["rmssd", "nremhr"]] = daily[["rmssd", "nremhr"]].replace(0, np.nan)
    # Resting HR for a date is computed from that whole day; use yesterday's to avoid peeking ahead.
    daily = daily.sort_values(["id", "date"])
    daily["resting_hr_prev"] = daily.groupby("id")["resting_hr"].shift(1)
    for c in OVERNIGHT + ["resting_hr_prev"]:
        g = daily.groupby("id")[c]
        daily[f"{c}_z"] = (daily[c] - g.transform("mean")) / g.transform("std")
    keyed = df.assign(date=df["ts"].dt.normalize())
    return keyed.merge(daily[["id", "date"] + GROUP_D], on=["id", "date"], how="left").drop(columns="date").set_index(df.index)


def add_group_e(df):
    daily = load_hourly(DEFAULT_DAILY_CSV)[["id", "age", "gender", "bmi"]].dropna().drop_duplicates("id")
    bmi = daily["bmi"].astype(str).str.replace("<", "", regex=False).str.replace(">=", "", regex=False)
    profile = pd.DataFrame({
        "id": daily["id"],
        "age_30plus": (daily["age"] == ">=30").astype(int),
        "female": (daily["gender"] == "FEMALE").astype(int),
        "bmi": pd.to_numeric(bmi, errors="coerce"),
    })
    surveys = DATA / "scored_surveys"
    stai = pd.read_csv(surveys / "stai.csv").sort_values("submitdate").drop_duplicates("user_id")
    traits = pd.read_csv(surveys / "personality.csv").sort_values("submitdate").drop_duplicates("user_id")
    profile = (profile
               .merge(stai[["user_id", "stai_stress"]].rename(columns={"user_id": "id", "stai_stress": "stai_first"}), on="id", how="left")
               .merge(traits[["user_id", "extraversion", "agreeableness", "conscientiousness", "stability", "intellect"]]
                      .rename(columns={"user_id": "id"}), on="id", how="left"))
    return df.merge(profile, on="id", how="left").set_index(df.index)


def person_normalize(df, features, skip=()):
    """z-score each feature within person (feature values only, no labels)."""
    out = df.copy()
    for c in features:
        if c in skip:
            continue
        g = out.groupby("id")[c]
        out[c] = (out[c] - g.transform("mean")) / g.transform("std")
    return out


def build_all(base_df, hr_by_id, steps_by_id):
    df = add_group_b(base_df, _person_tables(hr_by_id, steps_by_id))
    df = add_group_c(df)
    df = add_group_d(df)
    return add_group_e(df)
