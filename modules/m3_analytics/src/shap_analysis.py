"""shap_analysis.py — SHAP feature importance for the XGBoost classifiers.

Produces two figures (one per target) and a CSV of mean |SHAP value| per
feature, so we can defend XGBoost's predictions ("which features actually
drove the model?") rather than treating it as a black box.

Run:
    python -m src.shap_analysis
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from src.prediction import FEATURES, MODEL_COL

TARGETS = ["conversion", "drop_off"]


def _expand_feature_names(pipe) -> list[str]:
    """Pull human-readable feature names out of the fitted ColumnTransformer."""
    pre = pipe.named_steps["pre"]
    names: list[str] = []
    for name, trans, cols in pre.transformers_:
        if name == "cat":
            try:
                names.extend(trans.get_feature_names_out(cols).tolist())
            except Exception:
                names.extend(cols)
        elif name == "num":
            names.extend(cols)
    return names


def analyze_one(target: str, features_df: pd.DataFrame, models_dir: Path,
                figures_dir: Path, reports_dir: Path) -> pd.DataFrame:
    pipe = joblib.load(models_dir / f"{target}_xgboost.pkl")
    pre = pipe.named_steps["pre"]
    clf = pipe.named_steps["clf"]

    # Subsample for speed; SHAP on full data is fine but slower
    sample = features_df.sample(n=min(1000, len(features_df)), random_state=42)
    X_t = pre.transform(sample[FEATURES])
    feature_names = _expand_feature_names(pipe)

    explainer = shap.TreeExplainer(clf)
    shap_values = explainer.shap_values(X_t)

    # Mean absolute SHAP value per feature
    mean_abs = np.abs(shap_values).mean(axis=0)
    summary = pd.DataFrame({"feature": feature_names, "mean_abs_shap": mean_abs})
    summary = summary.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

    out_csv = reports_dir / f"shap_importance_{target}.csv"
    summary.to_csv(out_csv, index=False)

    # Bar plot of top 15
    top = summary.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(top["feature"], top["mean_abs_shap"], color="#4C72B0")
    ax.set_xlabel("Mean |SHAP value| (impact on model output)")
    ax.set_title(f"SHAP Feature Importance — {target.replace('_', ' ').title()}",
                 fontsize=13, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    out_fig = figures_dir / f"shap_importance_{target}.png"
    fig.savefig(out_fig, dpi=150)
    plt.close(fig)

    print(f"\n[{target}] Top 10 features by mean |SHAP|:")
    print(summary.head(10).to_string(index=False))
    print(f"Saved: {out_csv}")
    print(f"Saved: {out_fig}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="SHAP analysis for XGBoost models.")
    parser.add_argument("--features", default="data/processed/features.csv")
    parser.add_argument("--models-dir", default="outputs/models/")
    parser.add_argument("--figures-dir", default="outputs/figures/")
    parser.add_argument("--reports-dir", default="outputs/reports/")
    args = parser.parse_args()

    feats = pd.read_csv(args.features)
    figs = Path(args.figures_dir); figs.mkdir(parents=True, exist_ok=True)
    reps = Path(args.reports_dir); reps.mkdir(parents=True, exist_ok=True)
    mdls = Path(args.models_dir)

    for tgt in TARGETS:
        analyze_one(tgt, feats, mdls, figs, reps)


if __name__ == "__main__":
    main()
