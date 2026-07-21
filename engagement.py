"""Engagement model: feature extraction, training (RF + XGBoost), prediction."""

import re
import joblib
import numpy as np
import pandas as pd
import textstat
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from xgboost import XGBRegressor

import config

_sentiment = SentimentIntensityAnalyzer()

CTA_TERMS = [
    "buy", "shop", "start", "join", "learn", "discover", "try",
    "download", "register", "subscribe", "contact", "book", "order",
]


def _count_hashtags(t): return len(re.findall(r"#\w+", str(t)))
def _count_emojis(t):   return len(re.findall(r"[^\w\s,.!?']", str(t)))
def _has_cta(t):        return int(any(term in str(t).lower() for term in CTA_TERMS))
def _has_question(t):   return int("?" in str(t))


def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["text"] = df["text"].fillna("").astype(str)
    df["platform"] = df["platform"].fillna("unknown").astype(str).str.lower()

    df["char_length"] = df["text"].apply(len)
    df["word_count"] = df["text"].apply(lambda x: len(x.split()))
    df["hashtag_count"] = df["text"].apply(_count_hashtags)
    df["emoji_count"] = df["text"].apply(_count_emojis)
    df["cta_present"] = df["text"].apply(_has_cta)
    df["question_hook"] = df["text"].apply(_has_question)
    df["sentiment_score"] = df["text"].apply(
        lambda x: _sentiment.polarity_scores(x)["compound"]
    )
    df["readability_score"] = df["text"].apply(
        lambda x: textstat.flesch_reading_ease(x) if len(x.split()) > 3 else 0
    )
    df = pd.get_dummies(df, columns=["platform"], drop_first=False)
    return df


def _load_engagement_csv() -> pd.DataFrame:
    raw = pd.read_csv(config.ENGAGEMENT_DATASET_CSV)
    df = pd.DataFrame()
    df["platform"] = raw["platform"].fillna("unknown").astype(str).str.lower()
    df["text"] = raw["text"].fillna("").astype(str)
    df["likes"] = pd.to_numeric(raw["likes"], errors="coerce").fillna(0)
    df["comments"] = pd.to_numeric(raw["comments"], errors="coerce").fillna(0)
    df["shares"] = pd.to_numeric(raw["shares"], errors="coerce").fillna(0)
    df["impressions"] = pd.to_numeric(raw["impressions"], errors="coerce").fillna(1)
    df = df[df["text"].str.len() > 5]
    df = df[df["impressions"] > 0]
    df["engagement_rate"] = (df["likes"] + df["comments"] + df["shares"]) / df["impressions"]
    return df


def train():
    raw = _load_engagement_csv()
    features = extract_features(raw).fillna(0)
    target = "engagement_rate"
    feature_cols = [c for c in features.columns if c not in ("text", "engagement_rate")]

    X_tr, X_te, y_tr, y_te = train_test_split(
        features[feature_cols], features[target], test_size=0.20, random_state=42
    )

    rf = RandomForestRegressor(n_estimators=200, random_state=42).fit(X_tr, y_tr)
    # n_jobs=1: XGBoost's OpenMP pool clashes with torch's on macOS and can
    # segfault when this runs after torch has been loaded earlier in the run.
    xgb = XGBRegressor(
        n_estimators=300, learning_rate=0.05, max_depth=5, random_state=42, n_jobs=1
    ).fit(X_tr, y_tr)

    def _metrics(y_true, y_pred):
        return (
            mean_absolute_error(y_true, y_pred),
            float(np.sqrt(np.mean((y_true - y_pred) ** 2))),
            r2_score(y_true, y_pred),
        )

    rf_mae, rf_rmse, rf_r2 = _metrics(y_te, rf.predict(X_te))
    xgb_mae, xgb_rmse, xgb_r2 = _metrics(y_te, xgb.predict(X_te))

    results = pd.DataFrame(
        {
            "model": ["RandomForest", "XGBoost"],
            "MAE": [rf_mae, xgb_mae],
            "RMSE": [rf_rmse, xgb_rmse],
            "R2": [rf_r2, xgb_r2],
        }
    )
    print(results.to_string())
    results.to_csv(config.OUTPUTS / "engagement_model_comparison.csv", index=False)

    best_name = results.sort_values("R2", ascending=False).iloc[0]["model"]
    best = xgb if best_name == "XGBoost" else rf
    joblib.dump(best, config.ENGAGEMENT_MODEL_PKL)
    joblib.dump(feature_cols, config.ENGAGEMENT_FEATURES_PKL)
    print(f"Best engagement model: {best_name}")
    return best, feature_cols


def load() -> tuple:
    model = joblib.load(config.ENGAGEMENT_MODEL_PKL)
    feature_cols = joblib.load(config.ENGAGEMENT_FEATURES_PKL)
    return model, feature_cols


def _align(features: pd.DataFrame, feature_cols: list) -> pd.DataFrame:
    for col in feature_cols:
        if col not in features.columns:
            features[col] = 0
    return features[feature_cols]


def score(df: pd.DataFrame, model=None, feature_cols=None) -> pd.DataFrame:
    """Add predicted_engagement + normalized engagement_score columns. df must have caption + platform."""
    if model is None:
        model, feature_cols = load()
    pred_df = df.copy()
    pred_df["text"] = pred_df["caption"].fillna("").astype(str)
    pred_df["platform"] = pred_df["platform"].fillna("unknown").astype(str).str.lower()
    features = _align(extract_features(pred_df).fillna(0), feature_cols)
    df["predicted_engagement"] = model.predict(features)
    lo, hi = df["predicted_engagement"].min(), df["predicted_engagement"].max()
    df["engagement_score"] = (df["predicted_engagement"] - lo) / (hi - lo + 1e-8)
    return df
