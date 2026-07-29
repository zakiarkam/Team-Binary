"""Engagement model: feature extraction, training (RF + XGBoost), prediction."""

# Loaded first, on purpose: torch must initialise before xgboost or the
# process segfaults on macOS. See openmp_guard.py for the full explanation.
import openmp_guard  # noqa: F401  (import order matters)

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


#: Everything the model is allowed to see. Named explicitly rather than derived
#: by exclusion, because the previous version selected features by dropping only
#: "text" and "engagement_rate" — which silently left `likes`, `comments`,
#: `shares` and `impressions` in the feature set. The target is
#: (likes + comments + shares) / impressions, so the model was handed its own
#: answer and scored R² ≈ 0.99.
#:
#: The failure was invisible in training and fatal in production: a generated
#: caption has no like count, so at prediction time those four columns were
#: filled with zeros — far outside anything the model had seen — and the
#: engagement score that drives 45% of every content ranking became noise.
TEXT_FEATURES = [
    "char_length", "word_count", "hashtag_count", "emoji_count",
    "cta_present", "question_hook", "sentiment_score", "readability_score",
]

#: Columns that are outcomes, not inputs. Guarded by name so a future edit to
#: extract_features cannot reintroduce them.
LEAKY_COLUMNS = {"likes", "comments", "shares", "impressions", "engagement_rate"}


def model_feature_columns(features: pd.DataFrame) -> list[str]:
    """Text-derived features plus platform one-hots — and nothing else."""
    platform_cols = [c for c in features.columns if c.startswith("platform_")]
    cols = [c for c in TEXT_FEATURES if c in features.columns] + sorted(platform_cols)

    leaked = LEAKY_COLUMNS.intersection(cols)
    if leaked:                                    # pragma: no cover — guard
        raise ValueError(f"outcome columns must never be features: {sorted(leaked)}")
    return cols


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
    feature_cols = model_feature_columns(features)

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
        from scipy.stats import spearmanr

        # Spearman is the metric that matters here. The model exists to *order*
        # candidate captions, not to predict an engagement rate in absolute
        # terms, and rank correlation measures exactly that. R² is reported too,
        # and is expected to be poor: predicting engagement from wording alone,
        # with no audience or timing signal, is genuinely hard.
        rho = spearmanr(y_true, y_pred).statistic
        return (
            mean_absolute_error(y_true, y_pred),
            float(np.sqrt(np.mean((y_true - y_pred) ** 2))),
            r2_score(y_true, y_pred),
            float(rho) if rho == rho else 0.0,      # NaN-safe
        )

    rf_mae, rf_rmse, rf_r2, rf_rho = _metrics(y_te, rf.predict(X_te))
    xgb_mae, xgb_rmse, xgb_r2, xgb_rho = _metrics(y_te, xgb.predict(X_te))

    # A model that always predicts the training mean. Any real model must beat
    # it; without this baseline an R² near zero is hard to interpret.
    baseline_pred = np.full(len(y_te), y_tr.mean())
    b_mae, b_rmse, b_r2, b_rho = _metrics(y_te, baseline_pred)

    results = pd.DataFrame(
        {
            "model": ["Baseline (mean)", "RandomForest", "XGBoost"],
            "MAE": [b_mae, rf_mae, xgb_mae],
            "RMSE": [b_rmse, rf_rmse, xgb_rmse],
            "R2": [b_r2, rf_r2, xgb_r2],
            "Spearman": [b_rho, rf_rho, xgb_rho],
        }
    )
    print(results.to_string(index=False))
    results.to_csv(config.OUTPUTS / "engagement_model_comparison.csv", index=False)

    # Selected on rank correlation, since ranking is the job.
    trained = {"RandomForest": rf, "XGBoost": xgb}
    ranked = results[results.model != "Baseline (mean)"].sort_values(
        "Spearman", ascending=False)
    best_name = ranked.iloc[0]["model"]
    best = trained[best_name]

    joblib.dump(best, config.ENGAGEMENT_MODEL_PKL)
    joblib.dump(feature_cols, config.ENGAGEMENT_FEATURES_PKL)

    # Record measured skill next to the artifact so the Research page can report
    # what this model actually does rather than repeat a claim from a README.
    import json

    best_row = ranked.iloc[0]
    baseline_row = results[results.model == "Baseline (mean)"].iloc[0]
    beats_baseline = bool(best_row["R2"] > baseline_row["R2"])

    metrics = {
        "model": best_name,
        "features": feature_cols,
        "n_features": len(feature_cols),
        "n_rows": int(len(features)),
        "r2": round(float(best_row["R2"]), 4),
        "spearman": round(float(best_row["Spearman"]), 4),
        "mae": round(float(best_row["MAE"]), 4),
        "baseline_r2": round(float(baseline_row["R2"]), 4),
        "beats_baseline": beats_baseline,
        "leakage_guard": sorted(LEAKY_COLUMNS),
        "verdict": (
            "Usable as a ranker." if best_row["Spearman"] > 0.15 else
            "No demonstrated skill on this dataset — the ranking it produces is "
            "close to arbitrary, and its weight in the content score is set low "
            "accordingly."
        ),
    }
    (config.MODELS / "engagement_metrics.json").write_text(json.dumps(metrics, indent=2))

    print(f"\nBest engagement model: {best_name} "
          f"(Spearman {best_row['Spearman']:.3f}, R² {best_row['R2']:.3f})")
    print(f"Features ({len(feature_cols)}): {', '.join(feature_cols)}")
    print(f"Verdict: {metrics['verdict']}")
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
