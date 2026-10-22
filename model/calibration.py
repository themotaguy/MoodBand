"""Calibration check: do the Random Forest's and the SVM's probabilities mean what they say?

The feedback module acts on the top-class probability (min_confidence 0.45), so a
model is only usable there if its probabilities are trustworthy. For each held-out
mood report (participant-grouped 5-fold CV, 5 seeds, as in benchmark.py) this
compares the models' probabilities against what people reported:

  * balanced accuracy of the most probable class (for the SVM this can differ from
    SVC.predict, which ignores the Platt scaling)
  * Brier score and log loss (lower is better)
  * ECE: mean gap between top-class probability and accuracy, over 10 bins
  * AUC of top-class probability for "prediction is correct" (0.5 = confidence
    says nothing about correctness; decisions.md #11 found this for the RF)
  * accuracy above and below the 0.45 threshold

Writes model/results/calibration/{summary.csv, reliability.csv, reliability.png}.

Usage: python model/calibration.py
"""

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.impute import SimpleImputer
from sklearn.metrics import balanced_accuracy_score, log_loss, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from benchmark import CLASSES, GRID, SEEDS, SURFACE, TEXT, TEXT_2, models
from train_baseline import WINDOW_MIN
from windows import window_dataset

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results" / "calibration"
COLORS = {"Random Forest": "#2a78d6", "SVM (RBF)": "#eb6834"}  # dataviz categorical slots 1-2
THRESHOLD = 0.45  # feedback/decision.py Config.min_confidence
BINS = np.linspace(0, 1, 11)


def calibrated_models(seed):
    return {
        "Random Forest": models(seed)["Random Forest"],
        "SVM (RBF)": make_pipeline(SimpleImputer(), StandardScaler(),
                                   CalibratedClassifierCV(SVC(C=1.0, class_weight="balanced", random_state=seed), cv=5, ensemble=False)),
    }


def held_out_probabilities(X, y, groups):
    rows = []
    for seed in SEEDS:
        splits = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed).split(X, y, groups)
        for train, test in splits:
            for name, model in calibrated_models(seed).items():
                model.fit(X.iloc[train], y.iloc[train])
                proba = pd.DataFrame(model.predict_proba(X.iloc[test]), columns=model.classes_)[CLASSES]
                proba["model"], proba["seed"], proba["mood"] = name, seed, y.iloc[test].values
                rows.append(proba)
    return pd.concat(rows, ignore_index=True)


def summarize(p):
    probs = p[CLASSES].to_numpy()
    onehot = (p["mood"].to_numpy()[:, None] == np.array(CLASSES)).astype(float)
    top, pred = probs.max(axis=1), np.array(CLASSES)[probs.argmax(axis=1)]
    correct = pred == p["mood"].to_numpy()
    bin_ids = np.clip(np.digitize(top, BINS) - 1, 0, len(BINS) - 2)
    ece = sum((bin_ids == b).mean() * abs(top[bin_ids == b].mean() - correct[bin_ids == b].mean())
              for b in np.unique(bin_ids))
    above = top >= THRESHOLD
    return {
        "balanced_accuracy": balanced_accuracy_score(p["mood"], pred),
        "brier": ((probs - onehot) ** 2).sum(axis=1).mean(),
        "log_loss": log_loss(p["mood"], probs, labels=CLASSES),
        "ece": ece,
        "confidence_auc": roc_auc_score(correct, top),
        "top_prob_median": np.median(top),
        "share_above_threshold": above.mean(),
        "accuracy_above_threshold": correct[above].mean() if above.any() else np.nan,
        "accuracy_below_threshold": correct[~above].mean(),
        **{f"recall_{m}": (pred[p["mood"].to_numpy() == m] == m).mean() for m in CLASSES},
    }


def reliability(p):
    probs = p[CLASSES].to_numpy()
    top = probs.max(axis=1)
    correct = np.array(CLASSES)[probs.argmax(axis=1)] == p["mood"].to_numpy()
    b = pd.cut(top, BINS, include_lowest=True)
    return (pd.DataFrame({"bin": b, "top": top, "correct": correct})
            .groupby("bin", observed=True).agg(confidence=("top", "mean"), accuracy=("correct", "mean"),
                                                n=("correct", "size")).reset_index())


def plot(rel):
    fig, ax = plt.subplots(figsize=(6, 4.5), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=TEXT_2, labelsize=9)
    ax.plot([0, 1], [0, 1], color=GRID, linewidth=1.5, zorder=1)
    ax.text(0.83, 0.88, "perfectly\ncalibrated", color=TEXT_2, fontsize=8, ha="center")
    ax.axvline(THRESHOLD, color=TEXT_2, linewidth=1, linestyle=":", zorder=1)
    ax.text(THRESHOLD + 0.01, 0.02, "feedback threshold 0.45", color=TEXT_2, fontsize=8)
    for name, g in rel.groupby("model", sort=False):
        g = g[g["n"] >= 20]  # skip bins too small to read
        ax.plot(g["confidence"], g["accuracy"], color=COLORS[name], linewidth=2, marker="o", markersize=7,
                label=name, zorder=3)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.yaxis.grid(True, color=GRID, linewidth=1, zorder=0)
    ax.set_xlabel("Top-class probability (bins with ≥ 20 reports)", color=TEXT_2)
    ax.set_ylabel("Share of predictions that were correct", color=TEXT_2)
    ax.legend(frameon=False, loc="upper left", fontsize=9, labelcolor=TEXT)
    fig.suptitle("Does model confidence mean what it says?", color=TEXT, fontsize=12, x=0.01, ha="left")
    ax.set_title("LifeSnaps, held-out participants, 5 seeds", color=TEXT_2, fontsize=9, loc="left")
    fig.tight_layout()
    fig.savefig(RESULTS / "reliability.png", dpi=200)
    plt.close(fig)


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    X, y, groups, _ = window_dataset(WINDOW_MIN)
    probs = held_out_probabilities(X, y, groups)
    per_seed = pd.DataFrame([{"model": m, "seed": s, **summarize(g)}
                             for (m, s), g in probs.groupby(["model", "seed"], sort=False)])
    summary = per_seed.drop(columns="seed").groupby("model", sort=False).mean()
    summary.round(4).to_csv(RESULTS / "summary.csv")
    rel = pd.concat([reliability(g).assign(model=m) for m, g in probs.groupby("model", sort=False)])
    rel.round(4).to_csv(RESULTS / "reliability.csv", index=False)
    plot(rel)
    pd.set_option("display.width", 200)
    print(summary.round(3).T.to_string())
    print("\n" + rel.round(3).to_string(index=False))
    print(f"\nSaved results to {RESULTS}")


if __name__ == "__main__":
    main()
