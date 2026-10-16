"""PMData (Fitbit Versa 2, 16 participants) — secondary dataset, Docs/datasets.md.

Expected layout: data/pmdata/pXX/{fitbit,pmsys}/ as distributed.

Labels differ from LifeSnaps: PMSys wellness.csv has one report per day with
mood and stress each scored 1-5 (5 = best: very good mood / very relaxed; 0 is
invalid), not mood categories. So PMData is used to check whether the LifeSnaps
model's outputs track these scores (evaluate_pmdata.py), not as extra
4-class training data.

Fitbit timestamps are local time; PMSys timestamps are UTC and are converted
to Europe/Oslo (participants were in Norway).
"""

import json
import sys

import numpy as np
import pandas as pd

from lifesnaps import REPO_ROOT

DATA = REPO_ROOT / "data" / "pmdata"
TIMEZONE = "Europe/Oslo"


def participants():
    return sorted(p.name for p in DATA.glob("p[0-9][0-9]") if p.is_dir())


def extract_minutes():
    """Aggregate each participant's heart_rate.json / steps.json to minute files (one-off)."""
    hr_parts, step_parts = [], []
    for pid in participants():
        with open(DATA / pid / "fitbit" / "heart_rate.json") as f:
            recs = [(r["dateTime"][:16], r["value"]["bpm"]) for r in json.load(f)
                    if r["value"].get("confidence", 0) >= 1]
        hr = pd.DataFrame(recs, columns=["minute", "bpm"])
        hr = hr.groupby("minute")["bpm"].agg(bpm_mean="mean", bpm_std="std", n="size")
        hr["bpm_std"] = hr["bpm_std"].fillna(0)
        hr_parts.append(hr.round(2).reset_index().assign(id=pid))

        with open(DATA / pid / "fitbit" / "steps.json") as f:
            steps = pd.DataFrame([(r["dateTime"][:16], r["value"]) for r in json.load(f)],
                                 columns=["minute", "steps"])
        steps["steps"] = pd.to_numeric(steps["steps"], errors="coerce")
        step_parts.append(steps.groupby("minute", as_index=False)["steps"].sum().assign(id=pid))
        print(f"  {pid}: {len(hr):,} HR minutes, {len(steps):,} step minutes", flush=True)

    cols = ["id", "minute"]
    hr = pd.concat(hr_parts)
    hr[cols + ["bpm_mean", "bpm_std", "n"]].to_csv(DATA / "minute_hr.csv.gz", index=False)
    steps = pd.concat(step_parts)
    steps[cols + ["steps"]].to_csv(DATA / "minute_steps.csv.gz", index=False)


def load_reports():
    """Daily PMSys wellness reports: id, ts (local, naive), mood, stress (1-5)."""
    frames = []
    for pid in participants():
        w = pd.read_csv(DATA / pid / "pmsys" / "wellness.csv")
        ts = pd.to_datetime(w["effective_time_frame"], utc=True).dt.tz_convert(TIMEZONE)
        frames.append(pd.DataFrame({"id": pid, "ts": ts.dt.tz_localize(None).dt.floor("min"),
                                    "mood": w["mood"], "stress": w["stress"]}))
    df = pd.concat(frames, ignore_index=True)
    return df[df["mood"].between(1, 5) & df["stress"].between(1, 5)].reset_index(drop=True)


if __name__ == "__main__":
    extract_minutes()
