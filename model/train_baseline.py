"""Random Forest mood-classification baseline (Docs/decisions.md §6).

Two evaluations:
  * generalized  — participant-grouped cross-validation (no person appears in
                   both train and test), compared against a majority-class baseline.
  * personalized — per participant, train on the earliest 70% of their labels
                   and test on the latest 30% (paper [7]).

Usage: python model/train_baseline.py [path/to/hourly_fitbit_sema_df_unprocessed.csv]
"""

import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (balanced_accuracy_score, classification_report,
                             confusion_matrix, f1_score)
from sklearn.model_selection import StratifiedGroupKFold

from lifesnaps import DEFAULT_HOURLY_CSV, FEATURES, labelled_dataset

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
SEED = 42
MIN_LABELS_PERSONALIZED = 20


def make_rf():
    return RandomForestClassifier(
        n_estimators=300, min_samples_leaf=5, class_weight="balanced",
        n_jobs=-1, random_state=SEED,
    )


def generalized(X, y, groups):
    n_splits = min(5, groups.nunique())
    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    pred_rf = pd.Series(index=y.index, dtype=object)
    pred_dummy = pd.Series(index=y.index, dtype=object)
    for train, test in cv.split(X, y, groups):
        rf = make_rf().fit(X.iloc[train], y.iloc[train])
        pred_rf.iloc[test] = rf.predict(X.iloc[test])
        dummy = DummyClassifier(strategy="most_frequent").fit(X.iloc[train], y.iloc[train])
        pred_dummy.iloc[test] = dummy.predict(X.iloc[test])

    labels = sorted(y.unique())
    print(f"=== Generalized model: {n_splits}-fold participant-grouped CV ===")
    print(f"Majority-class baseline  macro-F1 {f1_score(y, pred_dummy, average='macro'):.3f}"
          f"   balanced acc {balanced_accuracy_score(y, pred_dummy):.3f}")
    print(f"Random Forest            macro-F1 {f1_score(y, pred_rf, average='macro'):.3f}"
          f"   balanced acc {balanced_accuracy_score(y, pred_rf):.3f}\n")
    print(classification_report(y, pred_rf, labels=labels, zero_division=0))
    print("Confusion matrix (rows = true, cols = predicted):")
    print(pd.DataFrame(confusion_matrix(y, pred_rf, labels=labels), index=labels, columns=labels))


def personalized(df):
    sort_cols = [c for c in ("date", "hour") if c in df]
    scores = []
    for pid, g in df.groupby("id"):
        if len(g) < MIN_LABELS_PERSONALIZED:
            continue
        g = g.sort_values(sort_cols)
        cut = int(len(g) * 0.7)
        train, test = g.iloc[:cut], g.iloc[cut:]
        if train["mood"].nunique() < 2:
            continue
        rf = make_rf().fit(train[FEATURES], train["mood"])
        with warnings.catch_warnings():
            # A participant's test slice often lacks some moods the model predicts.
            warnings.filterwarnings("ignore", message="y_pred contains classes not in y_true")
            scores.append(balanced_accuracy_score(test["mood"], rf.predict(test[FEATURES])))
    print(f"\n=== Personalized models: chronological 70/30 split per participant ===")
    if scores:
        print(f"Participants evaluated: {len(scores)}   balanced acc "
              f"mean {np.mean(scores):.3f}  median {np.median(scores):.3f}")
    else:
        print(f"No participant has >= {MIN_LABELS_PERSONALIZED} labels with 2+ moods.")


def main(path):
    X, y, groups, df = labelled_dataset(path)
    print(f"Labelled rows: {len(y):,}   participants: {groups.nunique()}   "
          f"classes: {dict(y.value_counts())}\n")
    generalized(X, y, groups)
    personalized(df)

    ARTIFACTS.mkdir(exist_ok=True)
    model = make_rf().fit(X, y)
    joblib.dump({"model": model, "features": FEATURES}, ARTIFACTS / "rf_baseline.joblib")
    importances = pd.Series(model.feature_importances_, index=FEATURES).sort_values(ascending=False)
    print("\nFeature importances (model fit on all data):")
    print(importances.round(3).to_string())
    print(f"\nSaved {ARTIFACTS / 'rf_baseline.joblib'}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOURLY_CSV)
