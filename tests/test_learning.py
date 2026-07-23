"""Tests for the opt-in engagement-learning subsystem.

These cover the parts that do not need torch/Phi-3: the relative target, the
feedback store round-trip, the CSV importer's column mapping, and a small
end-to-end retrain on synthetic data. The Phi-3-dependent candidate generation
is exercised only for its pure composite helper.
"""

import numpy as np
import pandas as pd
import pytest

import config
from learning import targets, feedback_store, importer, personalize, candidates


# --------------------------------------------------------------------------
# targets
# --------------------------------------------------------------------------

def test_engagement_rate_guards_zero_impressions():
    rate = targets.engagement_rate([10, 5], [2, 1], [1, 0], [0, 100])
    assert rate.iloc[0] == 0.0            # impressions=0 → 0, not inf
    assert rate.iloc[1] == pytest.approx(6 / 100)


def test_relative_target_removes_account_size_confound():
    # Two accounts, identical *relative* shape but wildly different scale.
    df = pd.DataFrame({
        "account_id": ["big"] * 5 + ["small"] * 5,
        "likes":      [100, 200, 300, 400, 500,  1, 2, 3, 4, 5],
        "comments":   [0] * 10,
        "shares":     [0] * 10,
        "impressions":[1000] * 5 + [10] * 5,
    })
    out = targets.relative_target(df, method="percentile", min_posts=3)
    assert out["target_is_relative"].all()
    # The top post of each account should get the same relative target despite
    # 100x difference in absolute likes.
    big_top = out[out["account_id"] == "big"]["target"].max()
    small_top = out[out["account_id"] == "small"]["target"].max()
    assert big_top == pytest.approx(small_top)


def test_relative_target_falls_back_without_accounts():
    df = pd.DataFrame({
        "likes": [10, 20], "comments": [0, 0], "shares": [0, 0],
        "impressions": [100, 100],
    })
    out = targets.relative_target(df, account_col=None)
    assert not out["target_is_relative"].any()
    assert out["target"].tolist() == pytest.approx([0.1, 0.2])


def test_relative_target_small_account_uses_raw_rate():
    df = pd.DataFrame({
        "account_id": ["a", "a", "solo"],
        "likes": [10, 20, 50], "comments": [0, 0, 0], "shares": [0, 0, 0],
        "impressions": [100, 100, 100],
    })
    out = targets.relative_target(df, method="zscore", min_posts=2)
    solo = out[out["account_id"] == "solo"].iloc[0]
    assert not solo["target_is_relative"]
    assert solo["target"] == pytest.approx(0.5)   # raw rate, not normalized


# --------------------------------------------------------------------------
# feedback_store
# --------------------------------------------------------------------------

@pytest.fixture()
def db(tmp_path):
    return tmp_path / "feedback.db"


def _asset(caption, platform="instagram", **extra):
    row = {"platform": platform, "caption": caption, "hashtags": ["#a", "#b"],
           "cta": "Buy now", "image_prompt": "a bottle", "shorts_prompt": "",
           "predicted_engagement": 0.3, "engagement_score": 0.8,
           "semantic_score": 0.7, "platform_suitability_score": 1.0,
           "final_score": 0.75}
    row.update(extra)
    return row


def test_store_logs_and_reports(db):
    df = pd.DataFrame([_asset("Hello world"), _asset("Second", platform="email")])
    n = feedback_store.log_assets(df, account_id="acct1", source="generated",
                                  db_path=db)
    assert n == 2
    summary = feedback_store.summary(db_path=db)
    assert summary["total_posts"] == 2
    assert summary["with_actuals"] == 0
    assert summary["accounts"] == 1


def test_store_matches_actuals_by_caption(db):
    feedback_store.log_assets(pd.DataFrame([_asset("Sip sustainably today")]),
                              account_id="acct1", db_path=db)
    matched, inserted = feedback_store.update_actuals(
        [{"caption": "Sip sustainably today!", "actual_likes": 50,
          "actual_comments": 5, "actual_shares": 2, "actual_impressions": 1000}],
        db_path=db,
    )
    assert matched == 1 and inserted == 0
    labeled = feedback_store.load_labeled(db_path=db)
    assert len(labeled) == 1
    assert labeled.iloc[0]["actual_engagement_rate"] == pytest.approx(57 / 1000)


def test_store_inserts_unmatched_history(db):
    matched, inserted = feedback_store.update_actuals(
        [{"caption": "An old post we never generated", "platform": "linkedin",
          "actual_likes": 10, "actual_impressions": 200}],
        db_path=db,
    )
    assert matched == 0 and inserted == 1
    assert feedback_store.summary(db_path=db)["with_actuals"] == 1


# --------------------------------------------------------------------------
# importer
# --------------------------------------------------------------------------

def test_importer_maps_generic_columns(tmp_path, db):
    csv = tmp_path / "export.csv"
    pd.DataFrame({
        "post text": ["Great product launch"],
        "likes": [120], "comments": [8], "shares": [4], "impressions": [3000],
    }).to_csv(csv, index=False)

    report = importer.import_csv(csv, account_id="acct1", db_path=db)
    assert report["rows"] == 1
    assert report["inserted"] == 1
    assert "actual_likes" in report["mapped_columns"]
    labeled = feedback_store.load_labeled(db_path=db)
    assert labeled.iloc[0]["actual_engagement_rate"] == pytest.approx(132 / 3000)


def test_importer_reports_unrecognized(tmp_path, db):
    csv = tmp_path / "weird.csv"
    pd.DataFrame({"foo": [1], "bar": [2]}).to_csv(csv, index=False)
    report = importer.import_csv(csv, db_path=db)
    assert report["rows"] == 0
    assert "error" in report


# --------------------------------------------------------------------------
# personalize (end-to-end on synthetic data, no torch)
# --------------------------------------------------------------------------

def test_retrain_on_synthetic_feedback(tmp_path, monkeypatch):
    # Point every artifact at a temp dir so the real repo is untouched.
    monkeypatch.setattr(config, "FEEDBACK_DB", tmp_path / "fb.db")
    monkeypatch.setattr(config, "PERSONALIZED_ENGAGEMENT_MODEL_PKL",
                        tmp_path / "model.pkl")
    monkeypatch.setattr(config, "PERSONALIZED_ENGAGEMENT_FEATURES_PKL",
                        tmp_path / "feat.pkl")
    monkeypatch.setattr(config, "PERSONALIZED_ENGAGEMENT_METRICS_JSON",
                        tmp_path / "metrics.json")
    monkeypatch.setattr(config, "RICH_ENGAGEMENT_DATASET_CSV",
                        tmp_path / "missing_rich.csv")
    monkeypatch.setattr(config, "ENGAGEMENT_DATASET_CSV",
                        tmp_path / "missing_base.csv")
    # Avoid the macOS torch↔XGBoost OpenMP segfault: sibling test modules import
    # transformers, and fitting XGBoost afterwards in the same process crashes.
    # The stage run standalone (no torch) still compares both models.
    monkeypatch.setattr(config, "LEARNING_SKIP_XGBOOST", True)

    rng = np.random.default_rng(0)
    rows = []
    for i in range(60):
        long = i % 2 == 0
        rows.append({
            "caption": ("Buy our amazing product now " * (6 if long else 1)).strip(),
            "platform": "instagram",
            "actual_likes": float(rng.integers(10, 100)),
            "actual_comments": float(rng.integers(0, 10)),
            "actual_shares": float(rng.integers(0, 5)),
            "actual_impressions": 1000.0,
            "account_id": f"acct{i % 4}",
        })
    feedback_store.update_actuals(rows, db_path=config.FEEDBACK_DB)

    metrics = personalize.retrain(method="percentile")
    assert metrics["n_rows"] > 0
    assert config.PERSONALIZED_ENGAGEMENT_MODEL_PKL.exists()

    bundle = personalize.load_bundle()
    assert bundle is not None
    assert "model" in bundle and "feature_cols" in bundle

    scored = personalize.score(
        pd.DataFrame([{"platform": "instagram", "caption": "Buy our product now"}]),
        account_id="acct0",
    )
    assert "engagement_score" in scored.columns
    assert 0.0 <= scored.iloc[0]["engagement_score"] <= 1.0


# --------------------------------------------------------------------------
# candidates (pure helper only — generation needs Phi-3)
# --------------------------------------------------------------------------

def test_composite_matches_weight_config():
    got = candidates._composite(1.0, 1.0, 1.0)
    assert got == pytest.approx(
        config.SEMANTIC_WEIGHT + config.PLATFORM_WEIGHT + config.ENGAGEMENT_WEIGHT
    )
    assert got == pytest.approx(1.0)
