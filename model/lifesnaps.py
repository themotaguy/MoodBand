"""Loading and label mapping for the LifeSnaps hourly Fitbit + SEMA3 CSV.

Expected input: hourly_fitbit_sema_df_unprocessed.csv (see Docs/datasets.md),
placed under data/lifesnaps/.

Feature policy follows Docs/decisions.md §3: only heart rate + motion are used
as real-time (waking-state) features. HRV is overnight-only and is NOT used here.
"""

from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HOURLY_CSV = REPO_ROOT / "data" / "lifesnaps" / "hourly_fitbit_sema_df_unprocessed.csv"

MOODBAND_CLASSES = ["happy", "neutral", "sad", "stressed", "angry"]

# SEMA3 mood column (upper-cased) -> MoodBand class.
# LifeSnaps' SEMA3 mood options do not line up 1:1 with MoodBand's five classes:
# there is no anger option ("angry" is deferred — Docs/decisions.md #7), and
# ALERT / TIRED / RESTED/RELAXED have no clean equivalent. Unmapped options are
# dropped rather than guessed.
SEMA_TO_MOODBAND = {
    "HAPPY": "happy",
    "NEUTRAL": "neutral",
    "SAD": "sad",
    "TENSE/ANXIOUS": "stressed",
}

# Raw real-time signals available from Fitbit via the Google Health API.
RAW_FEATURES = ["bpm", "steps"]


def load_hourly(path=DEFAULT_HOURLY_CSV):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Download LifeSnaps (Zenodo DOI 10.5281/zenodo.6826682) "
            "and place the hourly CSV there — see Docs/datasets.md."
        )
    df = pd.read_csv(path, low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    return df


def sema_mood_columns(df):
    """SEMA3 mood columns present in df, keyed by upper-cased name."""
    return {c.upper(): c for c in df.columns if c.upper() in SEMA_TO_MOODBAND
            or c.upper() in {"ALERT", "TIRED", "RESTED/RELAXED"}}


def add_mood_label(df, mapping=SEMA_TO_MOODBAND):
    """Add a `mood` column from one-hot SEMA3 mood columns.

    Rows with no mapped mood, or more than one, get NaN.
    """
    cols = {up: orig for up, orig in sema_mood_columns(df).items() if up in mapping}
    if not cols:
        raise ValueError("No SEMA3 mood columns found — check the CSV's column names.")
    onehot = df[list(cols.values())].fillna(0).astype(float) > 0
    onehot.columns = [mapping[up] for up in cols]
    n_selected = onehot.sum(axis=1)
    mood = onehot.idxmax(axis=1).where(n_selected == 1)
    return df.assign(mood=mood)


def add_features(df):
    """Real-time HR + motion features, plus per-participant HR baseline offset.

    The per-participant offset uses all of that participant's rows (labelled or
    not); in deployment this corresponds to a calibration period on the user's
    own unlabelled data, so it does not leak labels.
    """
    out = df.copy()
    for c in RAW_FEATURES:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    hr_mean = out.groupby("id")["bpm"].transform("mean")
    hr_std = out.groupby("id")["bpm"].transform("std").replace(0, np.nan)
    out["bpm_rel"] = out["bpm"] - hr_mean
    out["bpm_z"] = out["bpm_rel"] / hr_std
    out["hour"] = pd.to_numeric(out["hour"], errors="coerce")
    out["hour_sin"] = np.sin(2 * np.pi * out["hour"] / 24)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour"] / 24)
    return out


FEATURES = RAW_FEATURES + ["bpm_rel", "bpm_z", "hour_sin", "hour_cos"]


def labelled_dataset(path=DEFAULT_HOURLY_CSV):
    """(X, y, groups, df) for rows with a usable mood label and a heart-rate reading."""
    df = add_features(add_mood_label(load_hourly(path)))
    df = df[df["mood"].notna() & df["bpm"].notna()].reset_index(drop=True)
    return df[FEATURES], df["mood"], df["id"], df
