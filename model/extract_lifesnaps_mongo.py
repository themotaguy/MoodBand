"""One-off extraction of minute-level signals from the LifeSnaps MongoDB dump.

The hourly CSV averages heart rate over whole hours and only knows the hour of
each mood report. The raw dump has heart rate every few seconds and the exact
SEMA3 completion time, so features can be built from the minutes right before
each report. This script streams fitbit.bson (~9.7 GB) once and writes:

  data/lifesnaps/sema_responses.csv  id, completed_ts, mood, place
  data/lifesnaps/minute_hr.csv.gz    id, minute, bpm_mean, bpm_std, n  (confidence >= 1)
  data/lifesnaps/minute_steps.csv.gz id, minute, steps

Requires pymongo (for its bson module). No MongoDB server is needed.

Usage: python model/extract_lifesnaps_mongo.py [path/to/mongo_rais_anonymized]
"""

import struct
import sys
import time
from collections import Counter
from pathlib import Path

import bson
import numpy as np
import pandas as pd

from lifesnaps import REPO_ROOT

OUT = REPO_ROOT / "data" / "lifesnaps"
DEFAULT_DUMP = OUT / "mongo"
HR_TAG = b"\x02type\x00\x0b\x00\x00\x00heart_rate\x00"
STEPS_TAG = b"\x02type\x00\x06\x00\x00\x00steps\x00"
BATCH = 500_000


def iter_raw(path):
    """Yield each BSON document's raw bytes without decoding it."""
    with open(path, "rb") as f:
        while header := f.read(4):
            size = struct.unpack("<i", header)[0]
            yield header + f.read(size - 4)


def extract_sema(dump):
    rows = []
    with open(dump / "sema.bson", "rb") as f:
        for doc in bson.decode_file_iter(f):
            d = doc["data"]
            if d.get("COMPLETED_TS") and not str(d.get("MOOD", "<")).startswith("<"):
                rows.append((str(doc["user_id"]), d["COMPLETED_TS"], d["MOOD"], d.get("PLACE")))
    df = pd.DataFrame(rows, columns=["id", "completed_ts", "mood", "place"])
    df.to_csv(OUT / "sema_responses.csv", index=False)
    print(f"SEMA responses with a mood: {len(df):,} ({df['id'].nunique()} participants)")


def aggregate_hr(raw_docs, partials, confidence):
    rows = []
    for doc in bson.decode_all(b"".join(raw_docs)):
        v = doc["data"]["value"]
        confidence[v.get("confidence")] += 1
        if v.get("confidence", 0) >= 1:
            rows.append((str(doc["id"]), doc["data"]["dateTime"][:16], v["bpm"]))
    df = pd.DataFrame(rows, columns=["id", "minute", "bpm"])
    df["bpm2"] = df["bpm"].astype(float) ** 2
    partials.append(df.groupby(["id", "minute"]).agg(s=("bpm", "sum"), s2=("bpm2", "sum"),
                                                     n=("bpm", "size")))


def extract_fitbit(dump):
    hr_raw, step_rows, hr_partials = [], [], []
    confidence = Counter()
    t0 = time.time()
    for i, raw in enumerate(iter_raw(dump / "fitbit.bson"), 1):
        if HR_TAG in raw:
            hr_raw.append(raw)
            if len(hr_raw) >= BATCH:
                aggregate_hr(hr_raw, hr_partials, confidence)
                hr_raw = []
        elif STEPS_TAG in raw:
            doc = bson.decode(raw)
            step_rows.append((str(doc["id"]), doc["data"]["dateTime"][:16], doc["data"]["value"]))
        if i % 10_000_000 == 0:
            print(f"  {i / 1e6:.0f}M docs scanned, {time.time() - t0:.0f}s", flush=True)
    if hr_raw:
        aggregate_hr(hr_raw, hr_partials, confidence)
    print(f"Heart-rate readings by confidence: {dict(sorted(confidence.items(), key=str))}")

    # A minute can straddle two batches, so re-aggregate the partial sums.
    hr = pd.concat(hr_partials).groupby(level=[0, 1]).sum()
    hr["bpm_mean"] = hr["s"] / hr["n"]
    hr["bpm_std"] = np.sqrt(np.maximum(hr["s2"] / hr["n"] - hr["bpm_mean"] ** 2, 0))
    hr = hr[["bpm_mean", "bpm_std", "n"]].round(2).reset_index()
    hr.to_csv(OUT / "minute_hr.csv.gz", index=False)
    print(f"Minute heart-rate rows: {len(hr):,}")

    steps = pd.DataFrame(step_rows, columns=["id", "minute", "steps"])
    steps["steps"] = pd.to_numeric(steps["steps"], errors="coerce")
    steps = steps.groupby(["id", "minute"], as_index=False)["steps"].sum()
    steps.to_csv(OUT / "minute_steps.csv.gz", index=False)
    print(f"Minute step rows: {len(steps):,}   total time {time.time() - t0:.0f}s")


def main(dump):
    dump = Path(dump)
    OUT.mkdir(parents=True, exist_ok=True)
    extract_sema(dump)
    extract_fitbit(dump)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DUMP)
