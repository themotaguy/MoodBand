"""Random Forest mood-classification baseline (Docs/decisions.md §6).

The saved model uses the 30 minutes of heart rate and steps before each mood
report (windows.py, decisions.md #9). Hourly-CSV feature sets are evaluated
alongside it for comparison. Each is evaluated two ways:
  * generalized  — participant-grouped cross-validation (no person appears in
                   both train and test), compared against a majority-class baseline.
  * personalized — per participant, train on the earliest 70% of their labels
                   and test on the latest 30% (paper [7]).

Requires the minute-level files from extract_lifesnaps_mongo.py.

Usage: python model/train_baseline.py
"""

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

from lifesnaps import FEATURE_SETS, labelled_dataset
from windows import WINDOW_FEATURES, window_dataset

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
SEED = 42
MIN_LABELS_PERSONALIZED = 20
WINDOW_MIN = 30


def make_rf():
    return RandomForestClassifier(
        n_estimators=300, min_samples_leaf=5, class_weight="balanced",
        n_jobs=-1, random_state=SEED,
    )


def grouped_cv_predict(X, y, groups, make_model):
    cv = StratifiedGroupKFold(n_splits=min(5, groups.nunique()), shuffle=True, random_state=SEED)
    pred = pd.Series(index=y.index, dtype=object)
    for train, test in cv.split(X, y, groups):
        pred.iloc[test] = make_model().fit(X.iloc[train], y.iloc[train]).predict(X.iloc[test])
    return pred


def personalized(df, features):
    """Per-participant chronological 70/30 split; df needs id, ts, mood columns."""
    scores = []
    for pid, g in df.groupby("id"):
        if len(g) < MIN_LABELS_PERSONALIZED:
            continue
        g = g.sort_values("ts")
        cut = int(len(g) * 0.7)
        train, test = g.iloc[:cut], g.iloc[cut:]
        if train["mood"].nunique() < 2:
            continue
        rf = make_rf().fit(train[features], train["mood"])
        with warnings.catch_warnings():
            # A participant's test slice often lacks some moods the model predicts.
            warnings.filterwarnings("ignore", message="y_pred contains classes not in y_true")
            scores.append(balanced_accuracy_score(test["mood"], rf.predict(test[features])))
    return scores


def evaluate(name, X, y, groups, df, features):
    pred = grouped_cv_predict(X[features], y, groups, make_rf)
    pers = personalized(df, features)
    row = (name, len(y), f1_score(y, pred, average="macro"),
           balanced_accuracy_score(y, pred), np.mean(pers), len(pers))
    return row, pred


def report(y, pred):
    labels = sorted(y.unique())
    print(classification_report(y, pred, labels=labels, zero_division=0))
    print("Confusion matrix (rows = true, cols = predicted):")
    print(pd.DataFrame(confusion_matrix(y, pred, labels=labels), index=labels, columns=labels))


def main():
    Xw, yw, gw, dfw = window_dataset(WINDOW_MIN)
    print(f"Mood reports with >= 50% HR coverage in the prior {WINDOW_MIN} min: {len(yw):,}   "
          f"participants: {gw.nunique()}   classes: {yw.value_counts().to_dict()}\n")

    dummy = grouped_cv_predict(Xw, yw, gw, lambda: DummyClassifier(strategy="most_frequent"))
    rows = [("majority-class baseline", len(yw), f1_score(yw, dummy, average="macro"),
             balanced_accuracy_score(yw, dummy), np.nan, 0)]
    row, pred_w = evaluate(f"RF {WINDOW_MIN}-min window", Xw, yw, gw, dfw, WINDOW_FEATURES)
    rows.append(row)

    Xh, yh, gh, dfh = labelled_dataset()
    dfh["ts"] = pd.to_datetime(dfh["date"]) + pd.to_timedelta(dfh["hour"], unit="h")
    for name, features in FEATURE_SETS.items():
        rows.append(evaluate(f"RF hourly {name}", Xh, yh, gh, dfh, features)[0])

    summary = pd.DataFrame(rows, columns=["model", "n", "gen macro-F1", "gen bal-acc",
                                          "pers bal-acc", "pers n"]).set_index("model")
    print("=== Summary (gen = participant-grouped CV, pers = per-participant 70/30) ===")
    print(summary.round(3).to_string(), "\n")

    print(f"=== Generalized detail: RF {WINDOW_MIN}-min window ===")
    report(yw, pred_w)

    ARTIFACTS.mkdir(exist_ok=True)
    model = make_rf().fit(Xw, yw)
    joblib.dump({"model": model, "features": WINDOW_FEATURES, "window_min": WINDOW_MIN},
                ARTIFACTS / "rf_baseline.joblib")
    importances = pd.Series(model.feature_importances_, index=WINDOW_FEATURES)
    print("\nFeature importances (model fit on all data):")
    print(importances.sort_values(ascending=False).round(3).to_string())
    print(f"\nSaved {ARTIFACTS / 'rf_baseline.joblib'}")


if __name__ == "__main__":
    main()
