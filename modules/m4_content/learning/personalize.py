"""Retrain the engagement predictor on the base corpus + collected feedback.

Design constraints that shaped this module:

  * It writes to PERSONALIZED_ENGAGEMENT_MODEL_PKL, never to the base
    ENGAGEMENT_MODEL_PKL. The existing evaluate/optimize path keeps its model.
  * It reuses engagement.extract_features, so the personalized model consumes
    the same feature layout the base model does, plus a couple of account-level
    features. Candidate scoring can therefore use either model interchangeably.
  * The target is the content-relative one from targets.py, so the model learns
    "better than this account's baseline", not "big account". On the cold-start
    base corpus (no per-account history) this degrades gracefully to the raw
    engagement rate — the same quantity the base model already trains on.

The base corpus is the rich `Social Media Engagement Dataset.csv` when present
(it carries user_id + engagement_rate, which the relative target needs);
otherwise it falls back to the flat `your_engagement_dataset.csv`, in which case
every row is its own account and the target is just the raw rate.
"""

from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

import config
import engagement
from learning import feedback_store, targets

CANONICAL = ["text", "platform", "account_id", "likes", "comments",
             "shares", "impressions", "engagement_rate"]

# Column layout of the rich public corpus.
_RICH_MAP = {
    "text_content": "text",
    "user_id": "account_id",
    "likes_count": "likes",
    "comments_count": "comments",
    "shares_count": "shares",
    "impressions": "impressions",
    "engagement_rate": "engagement_rate",
    "platform": "platform",
}

ACCOUNT_FEATURES = ["account_baseline_rate", "account_post_count"]


def _empty_canonical() -> pd.DataFrame:
    return pd.DataFrame(columns=CANONICAL)


def load_base_corpus() -> pd.DataFrame:
    """Canonical base corpus, preferring the account-aware rich dataset."""
    if config.RICH_ENGAGEMENT_DATASET_CSV.exists():
        raw = pd.read_csv(config.RICH_ENGAGEMENT_DATASET_CSV)
        present = {src: dst for src, dst in _RICH_MAP.items() if src in raw.columns}
        frame = raw.rename(columns=present)
        for col in CANONICAL:
            if col not in frame.columns:
                frame[col] = np.nan
        return frame[CANONICAL].copy()

    if config.ENGAGEMENT_DATASET_CSV.exists():
        raw = pd.read_csv(config.ENGAGEMENT_DATASET_CSV)
        frame = _empty_canonical()
        for col in ("text", "platform", "likes", "comments", "shares",
                    "impressions"):
            frame[col] = raw[col] if col in raw.columns else np.nan
        frame["account_id"] = np.nan  # flat corpus has no accounts
        frame["engagement_rate"] = np.nan
        return frame

    return _empty_canonical()


def load_feedback_corpus() -> pd.DataFrame:
    """Canonical frame of feedback rows that carry observed analytics."""
    labeled = feedback_store.load_labeled()
    if labeled.empty:
        return _empty_canonical()
    frame = _empty_canonical()
    # The store keeps caption and hashtags in separate columns; the corpora keep
    # them together in one text field. Join them so feedback rows train on the
    # same shape of text the base corpus does.
    frame["text"] = engagement.scorable_text(labeled)
    frame["platform"] = labeled.get("platform")
    frame["account_id"] = labeled.get("account_id")
    frame["likes"] = labeled.get("actual_likes")
    frame["comments"] = labeled.get("actual_comments")
    frame["shares"] = labeled.get("actual_shares")
    frame["impressions"] = labeled.get("actual_impressions")
    if "actual_reach" in labeled:
        frame["impressions"] = frame["impressions"].fillna(labeled["actual_reach"])
    frame["engagement_rate"] = labeled.get("actual_engagement_rate")
    return frame


def build_training_frame(method: str = "percentile") -> pd.DataFrame:
    """Base + feedback, with the content-relative target attached."""
    combined = pd.concat(
        [load_base_corpus(), load_feedback_corpus()], ignore_index=True
    )
    combined = combined[combined["text"].fillna("").astype(str).str.len() > 5]
    combined = combined.reset_index(drop=True)
    if combined.empty:
        return combined

    labeled = targets.relative_target(
        combined,
        account_col="account_id",
        rate_col="engagement_rate",
        method=method,
        min_posts=config.RELATIVE_TARGET_MIN_ACCOUNT_POSTS,
    )

    baselines = targets.account_baseline(labeled)
    lookup = baselines.set_index("account_id")["baseline_rate"].to_dict()
    global_baseline = float(labeled["engagement_rate"].mean())
    counts = labeled["account_id"].map(labeled["account_id"].value_counts())

    # Leave-one-out, NOT the plain account mean: the mean is derived from the
    # target, and on a corpus of single-post accounts it *is* the target. See
    # targets.leave_one_out_baseline for the measured numbers. The full mean in
    # `lookup` is still what gets served at prediction time, where there is no
    # target to leak.
    labeled["account_baseline_rate"] = targets.leave_one_out_baseline(labeled)
    labeled["account_post_count"] = counts.fillna(0)
    labeled.attrs["global_baseline"] = global_baseline
    labeled.attrs["account_baselines"] = lookup
    return labeled


#: A feature this close to the target is not a feature, it is the answer. Both
#: leaks this project has found scored above 0.99 (the base model's outcome
#: columns, and this module's own account mean before it was made leave-one-out),
#: and both were invisible until someone looked at the number. So the check runs
#: on every retrain rather than living in a comment.
_LEAK_CORRELATION_LIMIT = 0.99


def _assert_no_leak(X: pd.DataFrame, y) -> None:
    """Raise if any feature is a near-perfect stand-in for the target."""
    leaked = engagement.LEAKY_COLUMNS.intersection(X.columns)
    if leaked:
        raise ValueError(f"outcome columns must never be features: {sorted(leaked)}")

    target = pd.Series(y, index=X.index, dtype="float64")
    if target.nunique() < 2:
        return
    for col in X.columns:
        values = pd.to_numeric(X[col], errors="coerce")
        if values.nunique() < 2:
            continue
        r = abs(float(target.corr(values)))
        if r == r and r >= _LEAK_CORRELATION_LIMIT:
            raise ValueError(
                f"feature {col!r} correlates {r:.4f} with the target — that is "
                "leakage, not skill. See targets.leave_one_out_baseline."
            )


def _build_xy(frame: pd.DataFrame):
    features = engagement.extract_features(frame).fillna(0)
    for col in ACCOUNT_FEATURES:
        features[col] = frame[col].to_numpy()
    feature_cols = [
        c for c in features.columns
        if c not in ("text", "engagement_rate", "target", "target_is_relative",
                     "account_id", "likes", "comments", "shares", "impressions")
    ]
    X = features[feature_cols]
    y = frame["target"].to_numpy()
    _assert_no_leak(X, y)
    return X, y, feature_cols


def _fit_and_select(X, y):
    """RF vs XGBoost. Held-out split when there is data for it, else in-sample."""
    can_split = len(X) >= 20
    if can_split:
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
    else:
        X_tr, X_te, y_tr, y_te = X, X, y, y

    def _score(model):
        pred = model.predict(X_te)
        return (
            float(mean_absolute_error(y_te, pred)),
            float(r2_score(y_te, pred)) if len(set(y_te)) > 1 else float("nan"),
        )

    rf = RandomForestRegressor(n_estimators=200, random_state=42).fit(X_tr, y_tr)
    rf_mae, rf_r2 = _score(rf)
    candidates = [("RandomForest", rf, rf_mae, rf_r2)]

    if not config.LEARNING_SKIP_XGBOOST:
        # n_jobs=1: XGBoost's OpenMP pool clashes with torch's on macOS.
        xgb = XGBRegressor(
            n_estimators=300, learning_rate=0.05, max_depth=5,
            random_state=42, n_jobs=1,
        ).fit(X_tr, y_tr)
        xgb_mae, xgb_r2 = _score(xgb)
        candidates.append(("XGBoost", xgb, xgb_mae, xgb_r2))

    def _key(entry):
        _, _, mae, r2 = entry
        return r2 if not np.isnan(r2) else -mae

    best_name, best, _, _ = max(candidates, key=_key)

    metrics = {
        "held_out": can_split,
        "n_rows": int(len(X)),
        "results": [
            {"model": name, "MAE": mae, "R2": r2}
            for name, _, mae, r2 in candidates
        ],
        "selected": best_name,
    }
    return best, best_name, metrics


def retrain(method: str = "percentile") -> dict:
    """Train the personalized predictor and persist it. Returns metrics."""
    config.init_dirs()
    frame = build_training_frame(method=method)
    if frame.empty:
        raise ValueError(
            "No training rows available. Provide a base engagement corpus "
            "(Social Media Engagement Dataset.csv or your_engagement_dataset.csv) "
            "or import analytics via `feedback-import`."
        )

    X, y, feature_cols = _build_xy(frame)
    best, best_name, metrics = _fit_and_select(X, y)

    relative_share = float(frame["target_is_relative"].mean())
    metrics.update({
        "method": method,
        "relative_target_share": relative_share,
        "n_feedback_rows": int((frame.get("target_is_relative")).sum()
                               if "target_is_relative" in frame else 0),
    })

    bundle = {
        "model": best,
        "feature_cols": feature_cols,
        "account_baselines": frame.attrs.get("account_baselines", {}),
        "global_baseline": frame.attrs.get("global_baseline", 0.0),
        "target_method": method,
    }
    joblib.dump(bundle, config.PERSONALIZED_ENGAGEMENT_MODEL_PKL)
    joblib.dump(feature_cols, config.PERSONALIZED_ENGAGEMENT_FEATURES_PKL)
    with open(config.PERSONALIZED_ENGAGEMENT_METRICS_JSON, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"Personalized engagement model: {best_name} "
          f"(rows={metrics['n_rows']}, relative target on "
          f"{relative_share:.0%} of rows)")
    print(f"Saved → {config.PERSONALIZED_ENGAGEMENT_MODEL_PKL}")
    return metrics


def load_bundle() -> dict | None:
    if not config.PERSONALIZED_ENGAGEMENT_MODEL_PKL.exists():
        return None
    return joblib.load(config.PERSONALIZED_ENGAGEMENT_MODEL_PKL)


def score(df: pd.DataFrame, account_id: str | None = None) -> pd.DataFrame:
    """Predict relative engagement for generated assets using the bundle.

    Falls back to the base engagement.score if no personalized model exists yet,
    so a caller never has to branch on whether retraining has happened.
    """
    bundle = load_bundle()
    if bundle is None:
        return engagement.score(df)

    out = df.copy()
    # Caption + hashtags, matching how the corpora carry them inline. See
    # engagement.hashtag_text for the measured skew this avoids.
    out["text"] = engagement.scorable_text(out)
    out["platform"] = out["platform"].fillna("unknown").astype(str).str.lower()

    baselines = bundle.get("account_baselines", {})
    global_baseline = bundle.get("global_baseline", 0.0)
    baseline_rate = baselines.get(account_id, global_baseline)
    out["account_baseline_rate"] = baseline_rate
    out["account_post_count"] = 0

    features = engagement.extract_features(out).fillna(0)
    for col in ACCOUNT_FEATURES:
        if col not in features.columns:
            features[col] = out[col].to_numpy()
    for col in bundle["feature_cols"]:
        if col not in features.columns:
            features[col] = 0
    X = features[bundle["feature_cols"]]

    out["predicted_engagement"] = bundle["model"].predict(X)
    lo, hi = out["predicted_engagement"].min(), out["predicted_engagement"].max()
    out["engagement_score"] = (out["predicted_engagement"] - lo) / (hi - lo + 1e-8)
    return out
