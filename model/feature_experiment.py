"""Feature experiment: does adding Fitbit-available signals improve mood detection?

Adds one feature group at a time (features_plus.py) to the 12 baseline window
features and evaluates the Random Forest and the SVM on the same
participant-grouped 5-fold splits and seeds as benchmark.py:

  A  baseline (12 features from the 30 min before each report)
  B  A + heart rate unexplained by activity, longer context, weekday
  C  B + calories and exercise sessions
  D  C + last night's physiology as personal deviations
  E  D + sign-up profile (age band, gender, BMI, STAI, Big Five)
  F  E with every time-varying feature z-scored within person

Writes model/results/feature_experiment/{summary.csv, per_seed.csv, feature_runs.png}.

Usage: python model/feature_experiment.py
"""

import textwrap
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.model_selection import StratifiedGroupKFold

from benchmark import CLASSES, GRID, SEEDS, SURFACE, TEXT, TEXT_2, fit, models
from features_plus import GROUP_B, GROUP_C, GROUP_D, GROUP_E, build_all, person_normalize
from train_baseline import WINDOW_MIN
from windows import WINDOW_FEATURES, load_minutes, window_dataset

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results" / "feature_experiment"
MODELS = ["Random Forest", "SVM (RBF)"]
COLORS = {"Random Forest": "#2a78d6", "SVM (RBF)": "#eb6834"}  # dataviz categorical slots 1-2

RUNS = {
    "A baseline": WINDOW_FEATURES,
    "B + activity-adjusted HR, context": WINDOW_FEATURES + GROUP_B,
    "C + calories, exercise": WINDOW_FEATURES + GROUP_B + GROUP_C,
    "D + last night (personal deviations)": WINDOW_FEATURES + GROUP_B + GROUP_C + GROUP_D,
    "E + sign-up profile": WINDOW_FEATURES + GROUP_B + GROUP_C + GROUP_D + GROUP_E,
}
STATIC = set(GROUP_E) | {"is_weekend", "hour_sin", "hour_cos"}


def evaluate(df, features, label):
    rows = []
    X, y, groups = df[features], df["mood"], df["id"]
    for seed in SEEDS:
        splits = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed).split(X, y, groups))
        for name in MODELS:
            model = models(seed)[name]
            pred = pd.Series(index=y.index, dtype=object)
            for train, test in splits:
                pred.iloc[test] = fit(name, model, X.iloc[train], y.iloc[train]).predict(X.iloc[test])
            rows.append({"run": label, "model": name, "seed": seed, "n_features": len(features),
                         "balanced_accuracy": balanced_accuracy_score(y, pred),
                         "macro_f1": f1_score(y, pred, average="macro", labels=CLASSES, zero_division=0)})
    print(f"  {label}: done", flush=True)
    return rows


def plot(summary):
    runs = list(dict.fromkeys(summary["run"]))
    fig, ax = plt.subplots(figsize=(9, 4.5), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=TEXT_2, labelsize=9)
    x = np.arange(len(runs))
    for name in MODELS:
        s = summary[summary["model"] == name].set_index("run").loc[runs]
        ax.errorbar(x, s["balanced_accuracy_mean"], yerr=s["balanced_accuracy_sd"], color=COLORS[name],
                    linewidth=2, marker="o", markersize=8, capsize=3, label=name, zorder=3)
        ax.text(x[-1] + 0.12, s["balanced_accuracy_mean"].iloc[-1], f"{name} {s['balanced_accuracy_mean'].iloc[-1]:.3f}",
                color=TEXT, fontsize=9, va="center")
    ax.set_xticks(x, [r.split(" ", 1)[0] + "\n" + textwrap.fill(r.split(" ", 1)[1], 16) for r in runs],
                  color=TEXT_2, fontsize=8)
    ax.yaxis.grid(True, color=GRID, linewidth=1, zorder=0)
    ax.set_xlim(-0.4, len(runs) - 0.4 + 1.3)
    ax.set_ylabel("Balanced accuracy (mean ± sd, 5 seeds)", color=TEXT_2)
    ax.legend(frameon=False, loc="lower left", fontsize=9, labelcolor=TEXT)
    fig.suptitle("Adding Fitbit-available feature groups, one at a time", color=TEXT, fontsize=12, x=0.01, ha="left")
    ax.set_title("LifeSnaps, unseen participants, 4 moods (chance 0.25)", color=TEXT_2, fontsize=9, loc="left")
    fig.tight_layout()
    fig.savefig(RESULTS / "feature_runs.png", dpi=200)
    plt.close(fig)


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    minutes = load_minutes()
    _, _, _, base = window_dataset(WINDOW_MIN, minutes)
    df = build_all(base, *minutes)
    coverage = df[GROUP_B + GROUP_C + GROUP_D + GROUP_E].notna().mean().round(2)
    print(f"{len(df):,} reports, {df['id'].nunique()} participants. Feature coverage (share non-missing):")
    print(coverage.to_string())

    rows = []
    for label, features in RUNS.items():
        rows += evaluate(df, features, label)
    all_features = RUNS["E + sign-up profile"]
    normalized = person_normalize(df, all_features, skip=STATIC)
    rows += evaluate(normalized, all_features, "F E, person-normalized")

    per_seed = pd.DataFrame(rows)
    per_seed.to_csv(RESULTS / "per_seed.csv", index=False)
    g = per_seed.groupby(["run", "model"], sort=False)
    summary = g.agg(n_features=("n_features", "first"),
                    balanced_accuracy_mean=("balanced_accuracy", "mean"),
                    balanced_accuracy_sd=("balanced_accuracy", "std"),
                    macro_f1_mean=("macro_f1", "mean")).reset_index()
    summary.round(4).to_csv(RESULTS / "summary.csv", index=False)
    plot(summary)
    pd.set_option("display.width", 200)
    print("\n" + summary.round(3).to_string(index=False))
    print(f"\nSaved results to {RESULTS}")


if __name__ == "__main__":
    main()
