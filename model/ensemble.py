"""Can combining models, or learning each person, raise accuracy? (decisions.md #19)

Prof. Zantout asked at the mid-term (Oct 28) whether different or multiple models
could raise accuracy. Two experiments on the benchmark's data and splits
(benchmark.py: 30-min LifeSnaps windows, participant-grouped 5-fold CV, 5 seeds):

A. Combining models (people the model has never seen). Scored on the argmax of
   the predicted probabilities, since that is what the feedback module acts on
   (decisions.md #17).
   - Random Forest alone (reference)
   - Soft voting: average the probabilities of RF, logistic regression and
     gradient boosting (+ the MLP in a second variant)
   - Stacking: a balanced logistic regression learns how to weigh the base
     models' probabilities. Its training inputs come from an inner
     participant-grouped CV, so it never sees probabilities for people a base
     model was trained on.

B. Learning each person. For each held-out person with enough reports, the
   first K reports in time stand in for their "Was this right?" answers; all
   methods are scored on the same later reports.
   - Global RF (trained on other people only)
   - Prior shift: the global RF's probabilities reweighted by how often this
     person reported each mood in their first K (smoothed)
   - Personal weighting: the RF retrained on other people + the person's first
     K reports, each weighted PERSONAL_WEIGHT times
   Two controls check that the sensors still matter: always predicting the
   person's most common mood so far (no sensor data), and the prior shift
   applied to the person's probabilities in random order (readings scrambled).

Writes to model/results/ensemble/: combining.csv, personal.csv, ensemble.png

Usage: python model/ensemble.py [--personal-only]
"""

import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import balanced_accuracy_score, f1_score, recall_score
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.utils.class_weight import compute_sample_weight

from benchmark import CLASSES, GRID, SEEDS, SURFACE, TEXT, TEXT_2, fit, models, style
from train_baseline import WINDOW_MIN
from windows import WINDOW_FEATURES, window_dataset

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results" / "ensemble"
K_VALUES = [10, 20, 40]     # personal labels available before scoring
MIN_SCORED = 10             # a person needs this many reports after the first K
PERSONAL_WEIGHT = 10
PRIOR_SMOOTHING = 2         # pseudo-counts per mood for the prior shift
VOTERS = {
    "Voting: RF + LR + boosting": ["Random Forest", "Logistic regression", "Gradient boosting"],
    "Voting: RF + LR + boosting + MLP": ["Random Forest", "Logistic regression", "Gradient boosting",
                                         "Neural network (MLP)"],
}
PERSONAL_METHODS = ["Global model", "Usual mood only (control)", "Prior shift, scrambled readings (control)",
                    "Prior shift", "Personal weighting"]
STACK_BASE = ["Random Forest", "Logistic regression", "Gradient boosting", "Neural network (MLP)"]


def proba(name, model, X_train, y_train, X_test):
    """Probabilities for X_test, columns in CLASSES order."""
    m = fit(name, clone(model), X_train, y_train)
    p = m.predict_proba(X_test)
    return pd.DataFrame(p, columns=m.classes_, index=X_test.index)[CLASSES].to_numpy()


def stacked(base, X_tr, y_tr, g_tr, X_te, seed):
    inner = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed).split(X_tr, y_tr, g_tr)
    oof = np.zeros((len(y_tr), len(base) * len(CLASSES)))
    for a, b in inner:
        oof[b] = np.hstack([proba(n, m, X_tr.iloc[a], y_tr.iloc[a], X_tr.iloc[b]) for n, m in base.items()])
    meta = LogisticRegression(class_weight="balanced", max_iter=2000).fit(oof, y_tr)
    test = np.hstack([proba(n, m, X_tr, y_tr, X_te) for n, m in base.items()])
    p = meta.predict_proba(test)
    return pd.DataFrame(p, columns=meta.classes_)[CLASSES].to_numpy()


def scores(y, p):
    pred = np.array(CLASSES)[p.argmax(axis=1)]
    recall = recall_score(y, pred, labels=CLASSES, average=None, zero_division=0)
    return {"balanced_accuracy": balanced_accuracy_score(y, pred),
            "macro_f1": f1_score(y, pred, labels=CLASSES, average="macro", zero_division=0),
            "share_confident": float((p.max(axis=1) >= 0.45).mean()),
            **{f"recall_{c}": r for c, r in zip(CLASSES, recall)}}


def combining(X, y, groups):
    rows = []
    for seed in SEEDS:
        base = models(seed)
        stack_base = {n: base[n] for n in STACK_BASE}
        probs = {k: np.zeros((len(y), len(CLASSES)))
                 for k in ["Random Forest", *VOTERS, "Stacking (4 models)"]}
        for train, test in StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed).split(X, y, groups):
            Xtr, ytr, Xte = X.iloc[train], y.iloc[train], X.iloc[test]
            each = {n: proba(n, base[n], Xtr, ytr, Xte) for n in STACK_BASE}
            probs["Random Forest"][test] = each["Random Forest"]
            for name, members in VOTERS.items():
                probs[name][test] = np.mean([each[n] for n in members], axis=0)
            probs["Stacking (4 models)"][test] = stacked(stack_base, Xtr, ytr, groups.iloc[train], Xte, seed)
        rows += [{"method": k, "seed": seed, **scores(y, p)} for k, p in probs.items()]
        print(f"  combining: seed {seed} done", flush=True)
    return pd.DataFrame(rows)


def shift(p, own, prior):
    """Reweight probabilities from the training mix of moods to this person's mix."""
    q = p * (own / prior)
    return q / q.sum(axis=1, keepdims=True)


def personal(X, y, groups, ts):
    rows = []
    for seed in SEEDS:
        rf = models(seed)["Random Forest"]
        rng = np.random.default_rng(seed)
        for train, test in StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed).split(X, y, groups):
            Xtr, ytr = X.iloc[train], y.iloc[train]
            glob = fit("Random Forest", clone(rf), Xtr, ytr)
            prior = ytr.value_counts(normalize=True)[CLASSES].to_numpy()
            test_people = groups.iloc[test]
            for k in K_VALUES:
                out = {m: ([], []) for m in PERSONAL_METHODS}
                for pid in test_people.unique():
                    idx = test_people.index[test_people == pid]
                    idx = ts.loc[idx].sort_values(kind="stable").index
                    if len(idx) < k + MIN_SCORED:
                        continue
                    first, rest = idx[:k], idx[k:]
                    p_glob = pd.DataFrame(glob.predict_proba(X.loc[rest]), columns=glob.classes_)[CLASSES].to_numpy()
                    counts = y.loc[first].value_counts().reindex(CLASSES, fill_value=0).to_numpy()
                    own = (counts + PRIOR_SMOOTHING) / (counts.sum() + PRIOR_SMOOTHING * len(CLASSES))
                    p_prior = shift(p_glob, own, prior)
                    # Controls: does the sensor reading matter once the person's usual moods are known?
                    p_usual = np.tile(np.eye(len(CLASSES))[counts.argmax()], (len(rest), 1))
                    p_scrambled = shift(p_glob[rng.permutation(len(rest))], own, prior)
                    Xp, yp = pd.concat([Xtr, X.loc[first]]), pd.concat([ytr, y.loc[first]])
                    w = compute_sample_weight("balanced", yp)
                    w[len(ytr):] *= PERSONAL_WEIGHT
                    m = clone(rf).set_params(class_weight=None).fit(Xp, yp, sample_weight=w)
                    p_pers = pd.DataFrame(m.predict_proba(X.loc[rest]), columns=m.classes_)[CLASSES].to_numpy()
                    for name, p in zip(PERSONAL_METHODS, [p_glob, p_usual, p_scrambled, p_prior, p_pers]):
                        out[name][0].append(y.loc[rest].to_numpy())
                        out[name][1].append(p)
                for name, (ys, ps) in out.items():
                    if ys:
                        rows.append({"k": k, "method": name, "seed": seed, "people": len(ys),
                                     "y": np.concatenate(ys), "p": np.vstack(ps)})
        print(f"  personal: seed {seed} done", flush=True)
    # Pool each seed's folds, then score.
    df = pd.DataFrame(rows)
    pooled = []
    for (k, method, seed), d in df.groupby(["k", "method", "seed"], sort=False):
        y_all, p_all = np.concatenate(list(d["y"])), np.vstack(list(d["p"]))
        pooled.append({"k": k, "method": method, "seed": seed, "people": int(d["people"].sum()),
                       "reports": len(y_all), **scores(y_all, p_all)})
    return pd.DataFrame(pooled)


def summarize(per_seed, by):
    g = per_seed.groupby(by, sort=False)
    cols = [c for c in per_seed.columns if c not in (*by, "seed")]
    out = g[cols].mean()
    out["balanced_accuracy_sd"] = g["balanced_accuracy"].std()
    return out


def plot(comb, pers):
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.2), facecolor=SURFACE, gridspec_kw={"width_ratios": [1.1, 1]})
    for ax in (a, b):
        style(ax)
        ax.xaxis.grid(False)
        ax.yaxis.grid(True, color=GRID, linewidth=1, zorder=0)
        ax.axhline(0.25, color=TEXT_2, linewidth=1, zorder=1)
    s = comb.iloc[::1]
    x = np.arange(len(s))
    colors = ["#2a78d6"] + ["#8fb6e8"] * (len(s) - 1)
    a.bar(x, s["balanced_accuracy"], width=0.55, color=colors, zorder=2)
    a.errorbar(x, s["balanced_accuracy"], yerr=s["balanced_accuracy_sd"], fmt="none", ecolor=TEXT_2, capsize=3, zorder=3)
    for xi, v in zip(x, s["balanced_accuracy"]):
        a.text(xi, v + 0.012, f"{v:.3f}", ha="center", color=TEXT, fontsize=10)
    import textwrap
    a.set_xticks(x, [textwrap.fill(n, 16) for n in s.index], color=TEXT, fontsize=9)
    a.set_ylim(0, 0.5)
    a.set_ylabel("Balanced accuracy (unseen people)", color=TEXT_2)
    a.set_title("A. Combining models", color=TEXT, fontsize=12, loc="left")

    markers = {"Global model": ("#52514e", "o", "-"), "Prior shift": ("#e0952b", "s", "-"),
               "Personal weighting": ("#2a78d6", "D", "-"),
               "Usual mood only (control)": ("#9c9a94", "v", ":"),
               "Prior shift, scrambled readings (control)": ("#e0952b", "^", ":")}
    for method, (c, mk, ls) in markers.items():
        d = pers.xs(method, level="method")
        b.errorbar(d.index, d["balanced_accuracy"], yerr=d["balanced_accuracy_sd"], color=c, marker=mk,
                   markersize=8, linewidth=2, linestyle=ls, capsize=3, label=method, zorder=3)
    people = pers.xs("Global model", level="method")["people"]
    b.set_xticks(K_VALUES, [f"first {k}\n({people[k]:.0f} people)" for k in K_VALUES], color=TEXT)
    b.set_xlabel("The person's own labelled reports used", color=TEXT_2)
    b.set_ylim(0, 0.5)
    b.set_title("B. Learning each person (scored on their later reports)", color=TEXT, fontsize=12, loc="left")
    b.legend(frameon=False, loc="lower right", fontsize=9, labelcolor=TEXT)
    fig.text(0.01, 0.01, "LifeSnaps, 4 moods, participant-grouped 5-fold CV, mean ± sd over 5 seeds. Line = chance (0.25).",
             color=TEXT_2, fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(RESULTS / "ensemble.png", dpi=200)
    plt.close(fig)


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    X, y, groups, df = window_dataset(WINDOW_MIN)
    X = X[WINDOW_FEATURES]
    print(f"{len(y):,} reports, {groups.nunique()} participants", flush=True)

    if "--personal-only" in sys.argv:  # reuse part A's saved results
        comb = pd.read_csv(RESULTS / "combining.csv", index_col="method")
    else:
        comb = summarize(combining(X, y, groups), ["method"])
        comb.round(4).to_csv(RESULTS / "combining.csv")
    pers = summarize(personal(X, y, groups, df["ts"]), ["k", "method"])
    pers.round(4).to_csv(RESULTS / "personal.csv")
    plot(comb, pers)

    pd.set_option("display.width", 200)
    print("\nA. Combining models\n" + comb.round(3).to_string())
    print("\nB. Learning each person\n" + pers.round(3).to_string())
    print(f"\nSaved results to {RESULTS}")


if __name__ == "__main__":
    main()
