"""prediction.py — Train and evaluate conversion / drop-off classifiers (Phase 4b)."""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

TARGETS   = ["conversion", "drop_off"]
MODEL_COL = {
    "conversion": "converted",
    "drop_off":   "dropped_off",
}
CATEGORICAL = ["segment", "strategy", "dominant_channel", "first_channel", "last_channel"]
NUMERICAL   = [
    "n_sent", "n_opens", "n_clicks", "journey_length",
    "avg_time_between_events_hours", "recency_days",
]
FEATURES = CATEGORICAL + NUMERICAL


def _preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
            ("num", StandardScaler(), NUMERICAL),
        ]
    )


def _classifiers() -> dict[str, object]:
    return {
        "logistic_regression": LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=42
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200, class_weight="balanced", random_state=42, n_jobs=-1
        ),
        "xgboost": XGBClassifier(
            n_estimators=200, learning_rate=0.05, max_depth=4,
            scale_pos_weight=None,  # set dynamically per target
            random_state=42, eval_metric="logloss", verbosity=0,
        ),
    }


def train_target(
    features_df: pd.DataFrame,
    target: str,
    models_dir: Path,
    reports_dir: Path,
) -> pd.DataFrame:
    """Train all three classifiers for one target. Returns metric rows."""
    target_col = MODEL_COL[target]
    X = features_df[FEATURES]
    y = features_df[target_col]

    pos_ratio = (y == 0).sum() / max((y == 1).sum(), 1)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    classifiers = _classifiers()
    # Tune XGBoost's scale_pos_weight for this target's imbalance
    classifiers["xgboost"].set_params(scale_pos_weight=pos_ratio)

    metric_rows = []
    for name, clf in classifiers.items():
        pipe = Pipeline([("pre", _preprocessor()), ("clf", clf)])

        # 5-fold CV on training set
        cv_aucs = cross_val_score(pipe, X_train, y_train, cv=cv,
                                  scoring="roc_auc", n_jobs=1)
        print(f"  [{target}] {name:<22} CV AUC = {cv_aucs.mean():.4f} ± {cv_aucs.std():.4f}")

        # Refit on full training set, evaluate on test
        pipe.fit(X_train, y_train)
        y_pred  = pipe.predict(X_test)
        y_proba = pipe.predict_proba(X_test)[:, 1]

        metric_rows.append({
            "target":    target,
            "model":     name,
            "accuracy":  round(accuracy_score(y_test, y_pred), 4),
            "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
            "recall":    round(recall_score(y_test, y_pred, zero_division=0), 4),
            "f1":        round(f1_score(y_test, y_pred, zero_division=0), 4),
            "auc":       round(roc_auc_score(y_test, y_proba), 4),
            "cv_auc_mean": round(cv_aucs.mean(), 4),
            "cv_auc_std":  round(cv_aucs.std(), 4),
        })

        # Save model
        out_path = models_dir / f"{target}_{name}.pkl"
        joblib.dump(pipe, out_path)
        print(f"    Saved: {out_path}")

    return pd.DataFrame(metric_rows)


def run(target: str, features_path: Path, models_dir: Path, reports_dir: Path) -> None:
    features_df = pd.read_csv(features_path)
    models_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = reports_dir / "model_metrics.csv"
    existing = (
        pd.read_csv(metrics_path)
        if metrics_path.exists()
        else pd.DataFrame()
    )

    targets_to_run = TARGETS if target == "all" else [target]
    new_rows = []
    for t in targets_to_run:
        print(f"\nTraining target: {t}")
        rows = train_target(features_df, t, models_dir, reports_dir)
        new_rows.append(rows)

    if new_rows:
        updated = pd.concat(
            [existing[~existing["target"].isin(targets_to_run)]
             if not existing.empty else existing]
            + new_rows,
            ignore_index=True,
        )
        updated.to_csv(metrics_path, index=False)
        print(f"\nMetrics saved: {metrics_path}")
        print(updated[["target", "model", "accuracy", "f1", "auc"]].to_string(index=False))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Train conversion/drop-off classifiers.")
    parser.add_argument("--target", default="all",
                        choices=["conversion", "drop_off", "all"])
    parser.add_argument("--model",  default="all",
                        help="all (default) — individual model names not yet wired")
    parser.add_argument("--features", default="data/processed/features.csv")
    parser.add_argument("--models-dir",  default="outputs/models/")
    parser.add_argument("--reports-dir", default="outputs/reports/")
    args = parser.parse_args()

    run(
        target=args.target,
        features_path=Path(args.features),
        models_dir=Path(args.models_dir),
        reports_dir=Path(args.reports_dir),
    )


if __name__ == "__main__":
    main()
