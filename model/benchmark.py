"""Benchmark mood classifiers against the Random Forest baseline (decisions.md #14).

Every model sees the same LifeSnaps data (30-min windows, windows.py) and the
same participant-grouped 5-fold splits, repeated over 5 seeds, so differences
come from the model alone. Models: majority class (floor), logistic regression
(linear reference), Random Forest (current baseline), gradient boosting, an RBF
SVM, and a small neural network (MLP). All use balanced class weighting; the
models are run with sensible defaults, not tuned.

Writes to model/results/benchmark/:
  summary.csv            mean ± sd of balanced accuracy and macro-F1, per-class recall
  confusion_matrices.csv out-of-fold counts summed over all seeds
  balanced_accuracy.png  model comparison against chance
  confusion_matrices.png row-normalized confusion matrix per model

Usage: python model/benchmark.py
"""

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.utils.class_weight import compute_sample_weight

from train_baseline import WINDOW_MIN
from windows import WINDOW_FEATURES, window_dataset

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results" / "benchmark"
SEEDS = range(5)
CLASSES = ["happy", "neutral", "sad", "stressed"]

# Chart tokens: dataviz reference palette (light mode).
SURFACE, TEXT, TEXT_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES = "#2a78d6"
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def models(seed):
    scaled = lambda clf: make_pipeline(SimpleImputer(), StandardScaler(), clf)  # noqa: E731
    return {
        "Majority class": DummyClassifier(strategy="most_frequent"),
        "Logistic regression": scaled(LogisticRegression(class_weight="balanced", max_iter=2000)),
        "Random Forest": RandomForestClassifier(
            n_estimators=300, min_samples_leaf=5, class_weight="balanced", n_jobs=-1, random_state=seed),
        "Gradient boosting": HistGradientBoostingClassifier(
            learning_rate=0.05, max_iter=200, max_leaf_nodes=15, class_weight="balanced", random_state=seed),
        "SVM (RBF)": scaled(SVC(C=1.0, class_weight="balanced", random_state=seed)),
        # MLPClassifier has no class_weight; balanced sample weights do the same job.
        "Neural network (MLP)": scaled(MLPClassifier(
            hidden_layer_sizes=(32, 16), alpha=1e-3, early_stopping=True, max_iter=1000, random_state=seed)),
    }


def fit(name, model, X, y):
    if name == "Neural network (MLP)":
        return model.fit(X, y, mlpclassifier__sample_weight=compute_sample_weight("balanced", y))
    return model.fit(X, y)


def run(X, y, groups):
    rows, cms = [], {}
    for seed in SEEDS:
        splits = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed).split(X, y, groups))
        for name, model in models(seed).items():
            pred = pd.Series(index=y.index, dtype=object)
            for train, test in splits:
                pred.iloc[test] = fit(name, model, X.iloc[train], y.iloc[train]).predict(X.iloc[test])
            cm = confusion_matrix(y, pred, labels=CLASSES)
            cms[name] = cms.get(name, 0) + cm
            recall = np.diag(cm) / cm.sum(axis=1)
            rows.append({"model": name, "seed": seed,
                         "balanced_accuracy": balanced_accuracy_score(y, pred),
                         "macro_f1": f1_score(y, pred, average="macro", labels=CLASSES, zero_division=0),
                         **{f"recall_{c}": r for c, r in zip(CLASSES, recall)}})
        print(f"  seed {seed} done", flush=True)
    return pd.DataFrame(rows), cms


def summarize(per_seed):
    g = per_seed.groupby("model", sort=False)
    out = pd.DataFrame({
        "balanced_accuracy_mean": g["balanced_accuracy"].mean(),
        "balanced_accuracy_sd": g["balanced_accuracy"].std(),
        "macro_f1_mean": g["macro_f1"].mean(),
        "macro_f1_sd": g["macro_f1"].std(),
        **{f"recall_{c}": g[f"recall_{c}"].mean() for c in CLASSES},
    })
    # Paired with the Random Forest: same seeds, same splits.
    rf = per_seed[per_seed["model"] == "Random Forest"].set_index("seed")["balanced_accuracy"]
    out["vs_rf_mean_diff"] = g.apply(lambda d: (d.set_index("seed")["balanced_accuracy"] - rf).mean())
    out["vs_rf_seeds_better"] = g.apply(lambda d: int((d.set_index("seed")["balanced_accuracy"] > rf).sum()))
    return out.sort_values("balanced_accuracy_mean", ascending=False)


def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=TEXT_2, labelsize=10)


def plot_scores(summary, n):
    s = summary.iloc[::-1]  # best at the top
    fig, ax = plt.subplots(figsize=(8, 4), facecolor=SURFACE)
    style(ax)
    y = np.arange(len(s))
    ax.barh(y, s["balanced_accuracy_mean"], height=0.45, color=SERIES, zorder=2)
    ax.errorbar(s["balanced_accuracy_mean"], y, xerr=s["balanced_accuracy_sd"], fmt="none",
                ecolor=TEXT_2, elinewidth=1, capsize=3, zorder=3)
    ax.axvline(0.25, color=TEXT_2, linewidth=1, zorder=1)
    ax.text(0.253, -0.62, "chance (0.25)", color=TEXT_2, fontsize=9, va="center")
    for yi, (m, sd) in enumerate(zip(s["balanced_accuracy_mean"], s["balanced_accuracy_sd"])):
        ax.text(m + sd + 0.006, yi, f"{m:.3f}", va="center", color=TEXT, fontsize=10)
    ax.set_yticks(y, s.index, color=TEXT)
    ax.set_xlim(0, max(0.45, (s["balanced_accuracy_mean"] + s["balanced_accuracy_sd"]).max() + 0.05))
    ax.xaxis.grid(True, color=GRID, linewidth=1, zorder=0)
    ax.set_ylim(-0.9, len(s) - 0.5)
    ax.set_xlabel("Balanced accuracy, mean ± sd over 5 seeds (3 distinct participant splits)", color=TEXT_2)
    fig.suptitle("Mood classifiers on unseen participants", color=TEXT, fontsize=13, x=0.01, ha="left")
    ax.set_title(f"LifeSnaps, {n:,} mood reports, 4 moods, participant-grouped 5-fold CV",
                 color=TEXT_2, fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(RESULTS / "balanced_accuracy.png", dpi=200)
    plt.close(fig)


def plot_confusion(cms, order):
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("seq_blue", SEQUENTIAL)
    fig, axes = plt.subplots(2, 3, figsize=(12, 8), facecolor=SURFACE)
    for ax, name in zip(axes.flat, order):
        cm = cms[name]
        share = cm / cm.sum(axis=1, keepdims=True)
        ax.imshow(share, cmap=cmap, vmin=0, vmax=1)
        for i in range(len(CLASSES)):
            for j in range(len(CLASSES)):
                ax.text(j, i, f"{share[i, j]:.0%}", ha="center", va="center", fontsize=10,
                        color="#ffffff" if share[i, j] > 0.5 else TEXT)
        ax.set_xticks(range(len(CLASSES)), CLASSES, color=TEXT_2, fontsize=9)
        ax.set_yticks(range(len(CLASSES)), CLASSES, color=TEXT_2, fontsize=9)
        ax.set_xlabel("Predicted", color=TEXT_2, fontsize=9)
        ax.set_ylabel("Reported", color=TEXT_2, fontsize=9)
        ax.set_title(name, color=TEXT, fontsize=11)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(length=0)
    fig.suptitle("Confusion matrices: share of each reported mood (rows sum to 100%), 5 seeds pooled",
                 color=TEXT, fontsize=12, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(RESULTS / "confusion_matrices.png", dpi=200)
    plt.close(fig)


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    X, y, groups, _ = window_dataset(WINDOW_MIN)
    X = X[WINDOW_FEATURES]
    print(f"{len(y):,} reports, {groups.nunique()} participants; {len(SEEDS)} seeds × 5 folds", flush=True)

    per_seed, cms = run(X, y, groups)
    summary = summarize(per_seed)
    summary.round(4).to_csv(RESULTS / "summary.csv")
    pd.concat({name: pd.DataFrame(cm, index=CLASSES, columns=CLASSES) for name, cm in cms.items()},
              names=["model", "reported"]).to_csv(RESULTS / "confusion_matrices.csv")
    plot_scores(summary, len(y))
    plot_confusion(cms, list(summary.index))

    pd.set_option("display.width", 200)
    print("\n" + summary.round(3).to_string())
    print(f"\nSaved results to {RESULTS}")


if __name__ == "__main__":
    main()
