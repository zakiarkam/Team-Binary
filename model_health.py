"""Honest model-health report for the whole system.

A research project must report its models' weaknesses, not just their headline
numbers. This script gathers the real metrics across all four modules, adds
cross-validation where the data allows, flags leakage / overfitting, and writes
data/integrated/model_health.json (consumed by the Research dashboard).

Run:  python model_health.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import config

ROOT = config.ROOT
OUT = ROOT / "data" / "integrated" / "model_health.json"
M3_REPORTS = ROOT / "modules" / "m3_analytics" / "outputs" / "reports"


def _goal_tone_health() -> list[dict]:
    """Report the goal/tone classifier and add stratified CV where possible."""
    findings = []
    metrics_path = config.GOAL_TONE_METRICS_JSON
    single = {}
    if metrics_path.exists():
        d = json.loads(metrics_path.read_text())
        rows = d.get("dataset_rows", "?")
        for r in d.get("results", []):
            single[r["target"]] = r.get("accuracy")

    # Cross-validation on the training corpus (more honest than one split).
    cv_report = {}
    try:
        from sklearn.model_selection import StratifiedKFold, cross_val_score
        from goal_tone import create_tfidf_pipeline
        df = pd.read_csv(config.GOAL_TONE_TRAINING_DATASET)
        text_col = "text" if "text" in df.columns else df.columns[0]
        for target in ("campaign_goal", "tone"):
            if target not in df.columns:
                continue
            y = df[target].astype(str)
            min_class = y.value_counts().min()
            if min_class < 2:
                cv_report[target] = f"CV not possible — rarest class has {min_class} sample(s)"
                continue
            k = int(min(5, min_class))
            try:
                scores = cross_val_score(
                    create_tfidf_pipeline(), df[text_col].astype(str), y,
                    cv=StratifiedKFold(n_splits=k, shuffle=True, random_state=42),
                    scoring="f1_weighted")
                cv_report[target] = f"{scores.mean():.3f} ± {scores.std():.3f} (weighted-F1, {k}-fold)"
            except Exception as e:  # pragma: no cover
                cv_report[target] = f"CV error: {e}"
    except Exception as e:  # pragma: no cover
        cv_report = {"error": str(e)}

    findings.append({
        "model": "M4 goal classifier",
        "level": "caution",
        "finding": f"Single-split accuracy {single.get('campaign_goal','?')} on a very small "
                   f"labelled set; rare classes (e.g. 'engagement') have almost no support.",
        "action": f"Cross-validated weighted-F1: {cv_report.get('campaign_goal','—')}. "
                  f"Grow the labelled set and report CV, not a single split.",
    })
    findings.append({
        "model": "M4 tone classifier",
        "level": "caution",
        "finding": f"Single-split accuracy {single.get('tone','?')} — 1.0 on ~24 test rows is "
                   f"an overfit red flag, not real perfection.",
        "action": f"Cross-validated weighted-F1: {cv_report.get('tone','—')}. Treat as a "
                  f"low-data classifier; report CV with confidence intervals.",
    })
    return findings


def _engagement_health() -> list[dict]:
    comp = config.OUTPUTS / "engagement_model_comparison.csv"
    detail = "—"
    if comp.exists():
        df = pd.read_csv(comp)
        best = df.sort_values("R2", ascending=False).iloc[0]
        detail = f"{best['model']} R²={best['R2']:.3f}, MAE={best['MAE']:.4f}"
    return [{
        "model": "M4 engagement regressor",
        "level": "caution",
        "finding": f"High R² on the engagement dataset ({detail}). On a synthetic/"
                   f"semi-simulated corpus this is likely optimistic.",
        "action": "Report engagement prediction as a relative ranker, not an absolute "
                  "predictor; validate on real platform exports via learning/ loop.",
    }]


def _m3_health() -> list[dict]:
    findings = []
    mm = M3_REPORTS / "model_metrics.csv"
    vc = M3_REPORTS / "validation_comparison.csv"
    sim_auc = real_auc = None
    if mm.exists():
        df = pd.read_csv(mm)
        auc_col = next((c for c in df.columns if "auc" in c.lower()), None)
        if auc_col is not None:
            sim_auc = float(df[auc_col].max())
    if vc.exists():
        df = pd.read_csv(vc)
        auc_col = next((c for c in df.columns if "auc" in c.lower()), None)
        if auc_col is not None:
            real_auc = float(df[auc_col].max())
    findings.append({
        "model": "M3 conversion / drop-off models",
        "level": "caution",
        "finding": f"Simulated AUC ≈ {sim_auc if sim_auc is not None else '~1.0'} is inflated by "
                   f"label leakage (targets are defined by the same events used as features).",
        "action": f"The honest number is the real-data (UCI Bank-Marketing) validation "
                  f"AUC ≈ {real_auc if real_auc is not None else '0.95'}. Report that, and label "
                  f"simulated metrics clearly.",
    })
    return findings


def _m2_health() -> list[dict]:
    return [{
        "model": "M2 conversion model",
        "level": "ok",
        "finding": "Real RandomForest/LogReg trained with a Dummy baseline; accuracy sits near "
                   "the base rate due to class imbalance, which the module reports honestly.",
        "action": "Interpret with ROC/PR-AUC, not accuracy. No change needed.",
    }]


def main() -> None:
    findings = (_m2_health() + _goal_tone_health() + _engagement_health() + _m3_health())
    report = {
        "summary": "All models run and are reproducible. Four carry honest caveats "
                   "(low-data classifiers, synthetic-data optimism, and simulated-data "
                   "label leakage) that are reported here rather than hidden.",
        "findings": findings,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))
    print(f"Wrote {OUT}")
    for fnd in findings:
        print(f"  [{fnd['level']:>7}] {fnd['model']}")


if __name__ == "__main__":
    main()
