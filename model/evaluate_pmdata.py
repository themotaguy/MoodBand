"""Cross-dataset check: does the LifeSnaps-trained model carry over to PMData?

PMData has daily 1-5 mood and stress scores rather than mood categories
(see pmdata.py), so instead of accuracy this measures whether the LifeSnaps
model's outputs move with those scores, using Spearman correlation:
  * P(stressed)        vs PMData stress  (5 = very relaxed, so expect < 0)
  * P(happy) - P(sad)  vs PMData mood    (expect > 0)
Both pooled across reports and within each participant (z-scored per person).

Reference: a Random Forest regressor trained on PMData itself with
leave-one-participant-out CV, showing how much signal PMData's own labels carry.

Requires: extract_lifesnaps_mongo.py and `python model/pmdata.py` run first.

Usage: python model/evaluate_pmdata.py
"""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, wilcoxon
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict

import pmdata
from train_baseline import SEED, WINDOW_MIN, make_rf
from windows import WINDOW_FEATURES, load_minutes, window_features, window_dataset


def zscore_within(s, groups):
    return s.groupby(groups).transform(lambda x: (x - x.mean()) / x.std())


def describe(name, score, label, groups, expected_sign):
    pooled = spearmanr(score, label).statistic
    within = spearmanr(zscore_within(score, groups), zscore_within(label.astype(float), groups),
                       nan_policy="omit").statistic
    per_person = pd.Series({pid: spearmanr(score[groups == pid], label[groups == pid]).statistic
                            for pid in groups.unique()}).dropna()
    agree = int((np.sign(per_person) == expected_sign).sum())
    p = wilcoxon(per_person).pvalue
    print(f"  {name:<40} pooled rho {pooled:+.3f}   within-person rho {within:+.3f}   "
          f"participants with expected sign {agree}/{len(per_person)} (Wilcoxon p={p:.2f})")


def main():
    print(f"Training on LifeSnaps ({WINDOW_MIN}-min windows)...")
    X_ls, y_ls, _, _ = window_dataset(WINDOW_MIN)
    model = make_rf().fit(X_ls, y_ls)

    reports = pmdata.load_reports()
    pm = window_features(reports, *load_minutes(pmdata.DATA), WINDOW_MIN)
    print(f"PMData reports: {len(reports):,}; with >= 50% HR coverage in the prior "
          f"{WINDOW_MIN} min: {len(pm):,} from {pm['id'].nunique()} participants")
    print(f"  mood   {pm['mood'].value_counts().sort_index().to_dict()}")
    print(f"  stress {pm['stress'].value_counts().sort_index().to_dict()}\n")

    proba = pd.DataFrame(model.predict_proba(pm[WINDOW_FEATURES]), columns=model.classes_)
    print("Mean predicted class probabilities on PMData:",
          proba.mean().round(3).to_dict(), "\n")

    print("=== LifeSnaps model applied to PMData (Spearman) ===")
    describe("P(stressed) vs stress (expect -)", proba["stressed"], pm["stress"], pm["id"], -1)
    describe("P(happy) - P(sad) vs mood (expect +)", proba["happy"] - proba["sad"],
             pm["mood"], pm["id"], +1)

    print("\n=== Reference: RF regressor trained on PMData, leave-one-participant-out ===")
    for target in ("stress", "mood"):
        reg = RandomForestRegressor(n_estimators=300, min_samples_leaf=5, n_jobs=-1, random_state=SEED)
        pred = pd.Series(cross_val_predict(reg, pm[WINDOW_FEATURES], pm[target], groups=pm["id"],
                                           cv=LeaveOneGroupOut()), index=pm.index)
        describe(f"predicted vs actual {target} (expect +)", pred, pm[target], pm["id"], +1)


if __name__ == "__main__":
    main()
