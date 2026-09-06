"""evaluation.py — Three comparison studies for Phase 5 evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import joblib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from sklearn.metrics import (
    ConfusionMatrixDisplay, RocCurveDisplay,
    confusion_matrix, roc_auc_score, roc_curve,
)
from sklearn.model_selection import train_test_split

from src.attribution import compare_to_ground_truth, attribution_mae
from src.funnel import compute_funnel, compute_dropoffs, funnel_by
from src.prediction import FEATURES, MODEL_COL

TARGETS = ["conversion", "drop_off"]
MODEL_NAMES = ["logistic_regression", "random_forest", "xgboost"]
MODEL_LABELS = {"logistic_regression": "Logistic Reg.", "random_forest": "Random Forest",
                "xgboost": "XGBoost"}
COLORS = {"logistic_regression": "#4C72B0", "random_forest": "#55A868", "xgboost": "#C44E52"}


# ---------------------------------------------------------------------------
# Study 1 — Attribution comparison
# ---------------------------------------------------------------------------

def attribution_comparison_study(
    events_df: pd.DataFrame,
    gt_df: pd.DataFrame,
    figures_dir: Path,
) -> pd.DataFrame:
    """Bar chart of platform credits + MAE table. Returns the comparison DataFrame."""
    comp = compare_to_ground_truth(events_df, gt_df, level="platform")
    mae  = attribution_mae(comp)

    platforms = comp["platform"].tolist()
    x = np.arange(len(platforms))
    width = 0.15
    cols_plot = {
        "Ground Truth": ("true_influence", "#333333"),
        "First-Touch":  ("first_touch",    "#4C72B0"),
        "Last-Touch":   ("last_touch",     "#C44E52"),
        "Multi-Touch":  ("multi_touch",    "#55A868"),
        "Markov":       ("markov",         "#8172B2"),
    }

    fig, axes = plt.subplots(1, 2, figsize=(15, 5))

    # Left: credit bars
    ax = axes[0]
    n_series = len(cols_plot)
    for i, (label, (col, color)) in enumerate(cols_plot.items()):
        offset = (i - (n_series - 1) / 2) * width
        ax.bar(x + offset, comp[col], width=width * 0.9, label=label, color=color, alpha=0.88)
    ax.set_xticks(x)
    ax.set_xticklabels(platforms, fontsize=9)
    ax.set_ylabel("Attribution credit", fontsize=11)
    ax.set_title("Platform Credits: 4 Models vs Ground Truth", fontsize=12, fontweight="bold")
    ax.legend(fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)

    # Right: MAE bars
    ax2 = axes[1]
    models  = list(mae.keys())
    label_map = {"first_touch": "First-Touch", "last_touch": "Last-Touch",
                 "multi_touch": "Multi-Touch", "markov": "Markov"}
    color_map = {"first_touch": "#4C72B0", "last_touch": "#C44E52",
                 "multi_touch": "#55A868", "markov": "#8172B2"}
    labels  = [label_map[m] for m in models]
    mcolors = [color_map[m] for m in models]
    bars = ax2.bar(labels, [mae[m] for m in models], color=mcolors, width=0.5)
    for bar, val in zip(bars, mae.values()):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.001,
                 f"{val:.4f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax2.set_ylabel("MAE vs ground truth", fontsize=11)
    ax2.set_title("Attribution Recovery Error (lower is better)", fontsize=12, fontweight="bold")
    ax2.set_ylim(0, max(mae.values()) * 1.4)
    ax2.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    out = figures_dir / "eval_attribution_study.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")
    return comp


# ---------------------------------------------------------------------------
# Study 2 — Model comparison (ROC + confusion matrices)
# ---------------------------------------------------------------------------

def _recreate_test_split(
    features_df: pd.DataFrame, target_col: str
) -> tuple[pd.DataFrame, pd.Series]:
    """Reproduce the same 80/20 test split used during training."""
    X = features_df[FEATURES]
    y = features_df[target_col]
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    return X_test, y_test


def model_comparison_study(
    features_df: pd.DataFrame,
    models_dir: Path,
    figures_dir: Path,
) -> pd.DataFrame:
    """ROC curves (one figure per target) + confusion matrices. Returns AUC summary."""
    rows = []

    for target in TARGETS:
        target_col = MODEL_COL[target]
        X_test, y_test = _recreate_test_split(features_df, target_col)

        # ---- ROC curves ----
        fig_roc, ax_roc = plt.subplots(figsize=(7, 5))
        ax_roc.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)

        # ---- Confusion matrices ----
        fig_cm, axes_cm = plt.subplots(1, 3, figsize=(14, 4))

        for i, name in enumerate(MODEL_NAMES):
            pipe = joblib.load(models_dir / f"{target}_{name}.pkl")
            y_proba = pipe.predict_proba(X_test)[:, 1]
            y_pred  = pipe.predict(X_test)
            auc = roc_auc_score(y_test, y_proba)

            fpr, tpr, _ = roc_curve(y_test, y_proba)
            ax_roc.plot(fpr, tpr, color=COLORS[name], lw=2,
                        label=f"{MODEL_LABELS[name]} (AUC={auc:.4f})")

            cm = confusion_matrix(y_test, y_pred)
            disp = ConfusionMatrixDisplay(confusion_matrix=cm,
                                          display_labels=["Neg", "Pos"])
            disp.plot(ax=axes_cm[i], colorbar=False, cmap="Blues")
            axes_cm[i].set_title(MODEL_LABELS[name], fontsize=11)

            rows.append({"target": target, "model": name, "test_auc": round(auc, 4)})

        ax_roc.set_xlabel("False Positive Rate", fontsize=11)
        ax_roc.set_ylabel("True Positive Rate", fontsize=11)
        ax_roc.set_title(f"ROC Curves — {target.replace('_',' ').title()}", fontsize=13,
                         fontweight="bold")
        ax_roc.legend(fontsize=9, loc="lower right")
        ax_roc.spines[["top", "right"]].set_visible(False)
        fig_roc.tight_layout()
        roc_path = figures_dir / f"eval_roc_{target}.png"
        fig_roc.savefig(roc_path, dpi=150)
        plt.close(fig_roc)
        print(f"Saved: {roc_path}")

        fig_cm.suptitle(f"Confusion Matrices — {target.replace('_',' ').title()}",
                        fontsize=13, fontweight="bold")
        fig_cm.tight_layout()
        cm_path = figures_dir / f"eval_cm_{target}.png"
        fig_cm.savefig(cm_path, dpi=150)
        plt.close(fig_cm)
        print(f"Saved: {cm_path}")

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Study 3 — Strategy comparison
# ---------------------------------------------------------------------------

def strategy_comparison_study(
    events_df: pd.DataFrame,
    features_df: pd.DataFrame,
    models_dir: Path,
    figures_dir: Path,
) -> pd.DataFrame:
    """Funnel rates + conversion AUC, broken down by strategy."""
    strategies = sorted(events_df["strategy"].unique())

    # Load best conversion model (XGBoost)
    conv_pipe = joblib.load(models_dir / "conversion_xgboost.pkl")

    rows = []
    for strat in strategies:
        # Funnel metrics from events
        strat_events = events_df[events_df["strategy"] == strat]
        funnel  = compute_funnel(strat_events)
        dropoff = compute_dropoffs(funnel)
        conv_rate = funnel["convert"] / funnel["sent"] if funnel["sent"] else 0

        # Prediction AUC for users in this strategy
        strat_feat = features_df[features_df["strategy"] == strat]
        if strat_feat["converted"].nunique() > 1:
            proba = conv_pipe.predict_proba(strat_feat[FEATURES])[:, 1]
            auc   = round(roc_auc_score(strat_feat["converted"], proba), 4)
        else:
            auc = float("nan")

        rows.append({
            "strategy":          strat,
            "n_sent":            funnel["sent"],
            "n_open":            funnel["open"],
            "n_click":           funnel["click"],
            "n_convert":         funnel["convert"],
            "conv_rate":         round(conv_rate, 4),
            "drop_sent_open":    dropoff["sent→open"],
            "drop_open_click":   dropoff["open→click"],
            "drop_click_convert":dropoff["click→convert"],
            "prediction_auc":    auc,
        })

    df = pd.DataFrame(rows)

    # ---- Plot ----
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Left: conversion rate bar
    ax1 = axes[0]
    colors_s = ["#4C72B0", "#55A868", "#C44E52"]
    bars = ax1.bar(df["strategy"], df["conv_rate"] * 100,
                   color=colors_s, width=0.45, edgecolor="white")
    for bar, val in zip(bars, df["conv_rate"]):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                 f"{val*100:.1f}%", ha="center", va="bottom", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Conversion rate (%)", fontsize=11)
    ax1.set_title("End-to-End Conversion Rate by Strategy", fontsize=12, fontweight="bold")
    ax1.spines[["top", "right"]].set_visible(False)

    # Right: drop-off rates stacked comparison
    ax2 = axes[1]
    x = np.arange(len(strategies))
    width = 0.25
    stage_cols = ["drop_sent_open", "drop_open_click", "drop_click_convert"]
    stage_labels = ["sent→open", "open→click", "click→convert"]
    drop_colors = ["#4C72B0", "#DD8452", "#C44E52"]
    for i, (col, label, color) in enumerate(zip(stage_cols, stage_labels, drop_colors)):
        ax2.bar(x + (i - 1) * width, df[col] * 100, width=width * 0.9,
                label=label, color=color, alpha=0.85)
    ax2.set_xticks(x)
    ax2.set_xticklabels(strategies, fontsize=10)
    ax2.set_ylabel("Drop-off rate (%)", fontsize=11)
    ax2.set_title("Drop-off Rates by Strategy and Stage", fontsize=12, fontweight="bold")
    ax2.legend(fontsize=9)
    ax2.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    out = figures_dir / "eval_strategy_comparison.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")
    return df


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Run all three evaluation studies.")
    parser.add_argument("--out", default="outputs/", help="Root outputs directory")
    args = parser.parse_args()

    out       = Path(args.out)
    figs_dir  = out / "figures"
    rep_dir   = out / "reports"
    mdl_dir   = out / "models"
    figs_dir.mkdir(parents=True, exist_ok=True)
    rep_dir.mkdir(parents=True, exist_ok=True)

    events   = pd.read_csv("data/simulated/event_logs.csv",   parse_dates=["timestamp"])
    gt       = pd.read_csv("data/simulated/ground_truth_influence.csv")
    features = pd.read_csv("data/processed/features.csv")

    print("=== Study 1: Attribution comparison ===")
    attribution_comparison_study(events, gt, figs_dir)

    print("\n=== Study 2: Model comparison ===")
    auc_df = model_comparison_study(features, mdl_dir, figs_dir)
    print(auc_df.to_string(index=False))

    print("\n=== Study 3: Strategy comparison ===")
    strat_df = strategy_comparison_study(events, features, mdl_dir, figs_dir)
    print(strat_df[["strategy", "conv_rate", "prediction_auc"]].to_string(index=False))
    strat_df.to_csv(rep_dir / "strategy_comparison.csv", index=False)
    print(f"Saved: {rep_dir / 'strategy_comparison.csv'}")


if __name__ == "__main__":
    main()
