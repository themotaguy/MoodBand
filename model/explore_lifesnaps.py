"""Exploratory checks on the LifeSnaps hourly CSV (Docs/datasets.md "Suggested next step").

Usage: python model/explore_lifesnaps.py [path/to/hourly_fitbit_sema_df_unprocessed.csv]
"""

import sys

from lifesnaps import (DEFAULT_HOURLY_CSV, MOODBAND_CLASSES, RAW_FEATURES,
                       add_mood_label, load_hourly, sema_mood_columns)


def main(path):
    df = load_hourly(path)
    print(f"Rows: {len(df):,}   Columns: {df.shape[1]}   Participants: {df['id'].nunique()}")
    if "date" in df:
        print(f"Date range: {df['date'].min()} -> {df['date'].max()}")
    print("\nColumns:\n ", ", ".join(df.columns))

    print("\nReal-time feature availability (non-null %):")
    for c in RAW_FEATURES + ["stress_score", "rmssd"]:
        if c in df:
            print(f"  {c:<14} {df[c].notna().mean():6.1%}")
        else:
            print(f"  {c:<14} MISSING")

    print("\nSEMA3 mood responses (raw options):")
    for up, col in sema_mood_columns(df).items():
        print(f"  {up:<16} {int((df[col].fillna(0).astype(float) > 0).sum()):>7,}")

    labelled = add_mood_label(df)
    labelled = labelled[labelled["mood"].notna()]
    print(f"\nRows with a single mapped MoodBand label: {len(labelled):,}")
    counts = labelled["mood"].value_counts()
    for cls in MOODBAND_CLASSES:
        n = int(counts.get(cls, 0))
        flag = "   <-- no data" if n == 0 else ""
        print(f"  {cls:<9} {n:>6,}  ({n / max(len(labelled), 1):5.1%}){flag}")

    usable = labelled[labelled["bpm"].notna()] if "bpm" in labelled else labelled.iloc[0:0]
    print(f"\n...of which have a heart-rate reading: {len(usable):,}")
    per_id = usable.groupby("id").size()
    if len(per_id):
        print(f"Labels per participant: median {per_id.median():.0f}, "
              f"min {per_id.min()}, max {per_id.max()}, "
              f"participants with >=20: {(per_id >= 20).sum()}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOURLY_CSV)
