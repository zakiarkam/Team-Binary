"""learned_recommender.py — XGBoost-based recommender as a learned alternative to rules.

Why
---
The hand-tuned thresholds in recommender.py (p_conv >= 0.7 -> premium offer, etc.)
are interpretable but subjective. This module trains an XGBoost classifier that
predicts the *most useful* action for each user, using converted outcomes as a
proxy label.

Label construction (proxy targets, not ground truth)
----------------------------------------------------
For each user we synthesise the "ideal action" label as follows:

    converted AND segment in {high_intent, loyal_customer}        -> send_premium_offer
    converted AND segment in {new_cold_customer, low_engagement}  -> send_personalized_offer
    dropped_off AND segment == price_sensitive                    -> send_reactivation_campaign
    everyone else                                                 -> send_general_reminder

This is a *weakly supervised* label — it's a proxy because we don't have
counterfactual data ("what would have happened if I sent this user X?").
We train the classifier and report agreement with the rule-based recommender
as a sanity check, plus held-out accuracy on the proxy label.

Run
---
    python -m src.learned_recommender
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from src.prediction import CATEGORICAL, FEATURES, NUMERICAL


ACTIONS = [
    "send_general_reminder",
    "send_personalized_offer",
    "send_premium_offer",
    "send_reactivation_campaign",
]


def _proxy_label(row: pd.Series) -> str:
    """Synthesise the 'ideal action' label using outcome + segment."""
    seg = row["segment"]
    if row["converted"] == 1 and seg in {"high_intent", "loyal_customer"}:
        return "send_premium_offer"
    if row["converted"] == 1 and seg in {"new_cold_customer", "low_engagement"}:
        return "send_personalized_offer"
    if row["dropped_off"] == 1 and seg == "price_sensitive":
        return "send_reactivation_campaign"
    return "send_general_reminder"


def _rule_label(p_conv: float, p_drop: float, segment: str) -> str:
    """Replicates the if/else thresholds in src/recommender.py."""
    if p_conv >= 0.7:
        return "send_premium_offer"
    if p_drop >= 0.6 and segment == "price_sensitive":
        return "send_reactivation_campaign"
    if p_conv >= 0.3:
        return "send_personalized_offer"
    return "send_general_reminder"


def _preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
            ("num", StandardScaler(), NUMERICAL),
        ]
    )


def train(
    features_path: Path,
    models_dir: Path,
    reports_dir: Path,
) -> dict:
    df = pd.read_csv(features_path)
    df["proxy_action"] = df.apply(_proxy_label, axis=1)

    le = LabelEncoder()
    y = le.fit_transform(df["proxy_action"])
    X = df[FEATURES]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    clf = XGBClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=4,
        objective="multi:softprob",
        num_class=len(le.classes_),
        random_state=42,
        eval_metric="mlogloss",
        verbosity=0,
        n_jobs=-1,
    )
    pipe = Pipeline([("pre", _preprocessor()), ("clf", clf)])
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(
        y_test, y_pred, target_names=le.classes_, zero_division=0, output_dict=True
    )

    # Compare against the rule-based recommender's choices on the test set
    conv_pipe = joblib.load(models_dir / "conversion_xgboost.pkl")
    drop_pipe = joblib.load(models_dir / "drop_off_xgboost.pkl")
    df_test = df.loc[X_test.index]
    p_conv = conv_pipe.predict_proba(df_test[FEATURES])[:, 1]
    p_drop = drop_pipe.predict_proba(df_test[FEATURES])[:, 1]
    rule_actions = [
        _rule_label(pc, pd_, seg)
        for pc, pd_, seg in zip(p_conv, p_drop, df_test["segment"])
    ]
    rule_idx = le.transform(rule_actions)
    agreement = float((rule_idx == y_pred).mean())
    rule_proxy_acc = float((rule_idx == y_test).mean())

    # Save model + label encoder
    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipe, "label_encoder": le},
                models_dir / "learned_recommender.pkl")

    summary = {
        "test_accuracy_learned":   round(float(acc), 4),
        "test_accuracy_rule":      round(rule_proxy_acc, 4),
        "agreement_learned_rule":  round(agreement, 4),
        "n_test":                  int(len(y_test)),
        "classes":                 le.classes_.tolist(),
    }

    # Per-class F1 summary
    f1_rows = []
    for cls in le.classes_:
        if cls in report:
            f1_rows.append({
                "class": cls,
                "precision": round(report[cls]["precision"], 4),
                "recall":    round(report[cls]["recall"], 4),
                "f1":        round(report[cls]["f1-score"], 4),
                "support":   int(report[cls]["support"]),
            })

    reports_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(f1_rows).to_csv(reports_dir / "learned_recommender_metrics.csv", index=False)
    pd.DataFrame([summary]).to_csv(reports_dir / "learned_recommender_summary.csv", index=False)

    print("\nLearned-recommender summary:")
    for k, v in summary.items():
        print(f"  {k:<26} {v}")
    print(f"\nSaved model:  {models_dir / 'learned_recommender.pkl'}")
    print(f"Saved metrics: {reports_dir / 'learned_recommender_metrics.csv'}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Train learned (XGBoost) recommender.")
    parser.add_argument("--features", default="data/processed/features.csv")
    parser.add_argument("--models-dir", default="outputs/models/")
    parser.add_argument("--reports-dir", default="outputs/reports/")
    args = parser.parse_args()
    train(Path(args.features), Path(args.models_dir), Path(args.reports_dir))


if __name__ == "__main__":
    main()
