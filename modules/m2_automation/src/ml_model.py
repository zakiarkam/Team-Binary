import os

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA_PATH = "data/processed/users_merged.csv"
SCORES_OUTPUT_PATH = "data/processed/users_with_ml_scores.csv"
REPORT_PATH = "outputs/ml_model_report.txt"

TARGET = "Conversion"

NUMERICAL_FEATURES = [
    "Age",
    "Income",
    "AdSpend",
    "ClickThroughRate",
    # ConversionRate correlates with Conversion at 0.093 (verified in Phase 1),
    # well below leakage threshold — kept as a legitimate feature, not dropped.
    "ConversionRate",
    "WebsiteVisits",
    "PagesPerVisit",
    "TimeOnSite",
    "SocialShares",
    "EmailOpens",
    "EmailClicks",
    "PreviousPurchases",
    "LoyaltyPoints",
    "engagement_score",
]

CATEGORICAL_FEATURES = [
    "Gender",
    "CampaignChannel",
    "CampaignType",
    "segment_name",
]


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer([
        ("num", StandardScaler(), NUMERICAL_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ])


def compute_metrics(model_name, y_true, y_pred, y_proba) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "model": model_name,
        "base_rate": y_true.mean(),
        "accuracy": accuracy_score(y_true, y_pred),
        "roc_auc": roc_auc_score(y_true, y_proba),
        "pr_auc": average_precision_score(y_true, y_proba),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
    }


def format_metrics_block(result: dict) -> str:
    return (
        f"Model: {result['model']}\n"
        f"  base_rate: {result['base_rate']:.4f}\n"
        f"  accuracy:  {result['accuracy']:.4f}\n"
        f"  roc_auc:   {result['roc_auc']:.4f}\n"
        f"  pr_auc:    {result['pr_auc']:.4f}\n"
        f"  precision: {result['precision']:.4f}\n"
        f"  recall:    {result['recall']:.4f}\n"
        f"  f1:        {result['f1']:.4f}\n"
        f"  confusion_matrix (tn, fp, fn, tp): {result['tn']}, {result['fp']}, {result['fn']}, {result['tp']}\n"
    )


def main():
    df = pd.read_csv(DATA_PATH)

    feature_cols = NUMERICAL_FEATURES + CATEGORICAL_FEATURES
    X = df[feature_cols]  # CustomerID explicitly excluded — identifier, not a feature
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    results = []

    # --- Dummy baseline ---
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(X_train, y_train)
    dummy_pred = dummy.predict(X_test)
    dummy_proba = dummy.predict_proba(X_test)[:, 1]
    dummy_result = compute_metrics("dummy", y_test, dummy_pred, dummy_proba)
    results.append(dummy_result)

    # --- Logistic Regression ---
    lr_pipeline = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("classifier", LogisticRegression(max_iter=2000, random_state=42)),
    ])
    lr_pipeline.fit(X_train, y_train)
    lr_pred = lr_pipeline.predict(X_test)
    lr_proba = lr_pipeline.predict_proba(X_test)[:, 1]
    lr_result = compute_metrics("logistic_regression", y_test, lr_pred, lr_proba)
    results.append(lr_result)

    # --- Random Forest ---
    rf_pipeline = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("classifier", RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1)),
    ])
    rf_pipeline.fit(X_train, y_train)
    rf_pred = rf_pipeline.predict(X_test)
    rf_proba = rf_pipeline.predict_proba(X_test)[:, 1]
    rf_result = compute_metrics("random_forest", y_test, rf_pred, rf_proba)
    results.append(rf_result)

    for result in results:
        print(format_metrics_block(result))

    base_rate = dummy_result["base_rate"]
    dummy_acc = dummy_result["accuracy"]
    rf_acc = rf_result["accuracy"]
    lr_auc = lr_result["roc_auc"]
    rf_auc = rf_result["roc_auc"]
    lr_pr = lr_result["pr_auc"]
    rf_pr = rf_result["pr_auc"]
    auc_gap = rf_auc - lr_auc
    interaction_note = (
        "meaningful interaction structure"
        if auc_gap > 0.02
        else "mostly linear signal with limited interaction structure"
    )

    interpretation = (
        f"Base rate: {base_rate:.4f}. Dummy accuracy: {dummy_acc:.4f}.\n"
        f"Random Forest accuracy: {rf_acc:.4f} — this is NOT the headline metric; "
        f"it barely exceeds the dummy floor because of class imbalance.\n"
        f"ROC-AUC: LR={lr_auc:.3f}, RF={rf_auc:.3f}. Values above 0.5 indicate "
        f"discrimination above chance; interpret modestly.\n"
        f"PR-AUC: LR={lr_pr:.3f}, RF={rf_pr:.3f}. The baseline for PR-AUC on this "
        f"dataset is the base rate itself ({base_rate:.3f}), so values only "
        f"meaningfully above that floor indicate real precision-recall performance "
        f"on the positive class.\n"
        f"The RF-over-LR gap on ROC-AUC ({auc_gap:.3f}) indicates {interaction_note} "
        f"in the features."
    )
    print(interpretation)

    # --- Feature importances (from the evaluated RF, trained on the 80% split) ---
    feature_names = rf_pipeline.named_steps["preprocessor"].get_feature_names_out()
    importances = rf_pipeline.named_steps["classifier"].feature_importances_
    importance_df = (
        pd.DataFrame({"feature": feature_names, "importance": importances})
        .sort_values("importance", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    print("\n=== Top-10 Random Forest feature importances ===")
    print(importance_df.to_string(index=False))

    # --- Refit RF on the FULL dataset to emit ml_score for all 8000 users ---
    final_rf_pipeline = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("classifier", RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1)),
    ])
    final_rf_pipeline.fit(X, y)
    ml_scores = final_rf_pipeline.predict_proba(X)[:, 1]

    df_out = df.copy()
    df_out["ml_score"] = ml_scores
    df_out.to_csv(SCORES_OUTPUT_PATH, index=False)

    print("\n=== ml_score.describe() (overall) ===")
    print(df_out["ml_score"].describe())

    print("\n=== ml_score.describe() (by segment_name) ===")
    print(df_out.groupby("segment_name")["ml_score"].describe())

    # --- Write text report ---
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        for result in results:
            f.write(format_metrics_block(result))
            f.write("\n")
        f.write("=== Top-10 Random Forest feature importances ===\n")
        f.write(importance_df.to_string(index=False))
        f.write("\n\n")
        f.write(interpretation)
        f.write("\n")


if __name__ == "__main__":
    main()
