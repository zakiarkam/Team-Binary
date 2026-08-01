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


def test_leave_one_out_baseline_excludes_the_row_itself():
    df = pd.DataFrame({
        "account_id": ["a", "a", "a", "solo"],
        "engagement_rate": [0.1, 0.2, 0.6, 0.9],
    })
    loo = targets.leave_one_out_baseline(df)
    assert list(loo[:3]) == pytest.approx([0.4, 0.35, 0.15])
    # a single-post account gets the constant global mean, never a value that
    # varies with its own rate
    assert loo.iloc[3] == pytest.approx(0.45)


def test_single_post_corpus_baseline_carries_no_row_information():
    """The leak this guards: on a corpus of one-post accounts the plain account
    mean IS the target (corr 1.000, R² 0.995 against -0.17 without it), and the
    leave-one-out *global* mean is the same leak with the sign flipped."""
    df = pd.DataFrame({
        "account_id": [f"acct{i}" for i in range(6)],
        "engagement_rate": [0.1, 0.25, 0.4, 0.55, 0.7, 0.9],
    })
    loo = targets.leave_one_out_baseline(df)
    assert loo.nunique() == 1, "must be constant when no account has history"
    assert loo.std(ddof=0) == pytest.approx(0.0)


def test_build_xy_refuses_a_feature_that_is_the_target():
    from learning import personalize

    frame = pd.DataFrame({
        "text": [f"caption number {i} about a product" for i in range(12)],
        "platform": ["instagram"] * 12,
        "target": [i / 12 for i in range(12)],
        "target_is_relative": [False] * 12,
        "account_baseline_rate": [i / 12 for i in range(12)],   # the leak
        "account_post_count": [1] * 12,
    })
    with pytest.raises(ValueError, match="leakage, not skill"):
        personalize._build_xy(frame)


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
# importer — per-platform export layouts
#
# One case per platform, using that platform's export headers rather than the
# store's canonical names. The previous synthetic fixture wrote canonical
# headers, so every layout passed while real TikTok/Facebook/YouTube exports
# imported zero rows: the mapping layer was never exercised. These cases feed
# the header spellings the alias lists claim to support, so a change that
# breaks one is caught here.
#
# NOTE: passing these does NOT prove the aliases match what a platform really
# ships today — export schemas change and none of this is verified against a
# real file. It proves the mapping and detection machinery works for the
# spellings we claim. Real files are checked with `importer.inspect_csv`.
# --------------------------------------------------------------------------

PLATFORM_EXPORTS = {
    "instagram": {
        # Account username and Saves are what distinguish an Instagram export
        # from a Facebook one — both otherwise carry Post ID / Description /
        # Reach / Likes / Comments / Shares. See the ambiguity test below for
        # what happens when a trimmed export has neither.
        "Post ID": "IG-1", "Account username": "brand",
        "Description": "Sip sustainably every morning",
        "Publish time": "2026-02-01", "Views": 4000, "Reach": 3200,
        "Likes": 210, "Comments": 14, "Shares": 6, "Saves": 30,
    },
    "facebook": {
        "Post ID": "FB-1", "Page ID": "PAGE-9", "Title": "Launch",
        "Description": "Meet the new insulated bottle", "Reach": 2800,
        "Impressions": 3500, "Reactions": 180, "Comments": 11, "Shares": 5,
    },
    "linkedin": {
        "Post link": "https://linkedin.com/feed/update/1",
        "Post title": "Why we rebuilt our scheduling tool",
        "Date": "2026-02-01", "Impressions": 5200, "Clicks": 140,
        "Likes": 96, "Comments": 7, "Reposts": 3,
    },
    "tiktok": {
        "Video link": "https://tiktok.com/@x/video/1",
        "Video title": "POV: your morning just got easier",
        "Post time": "2026-02-01", "Video views": 22000,
        "Likes": 1400, "Comments": 62, "Shares": 88,
    },
    "youtube": {
        "Content": "YT-1", "Video title": "The 30-second setup",
        "Video publish time": "2026-02-01", "Impressions": 9000, "Views": 3100,
        "Likes": 240, "Comments added": 18, "Shares": 12,
    },
    "email": {
        "Campaign ID": "EM-1", "Subject line": "Your next small upgrade",
        "Send date": "2026-02-01", "Delivered": 12000, "Unique opens": 3400,
        "Unique clicks": 410, "Unsubscribes": 9,
    },
}


@pytest.mark.parametrize("platform", sorted(PLATFORM_EXPORTS))
def test_importer_handles_real_export_headers(platform, tmp_path, db):
    """Each platform's export layout maps and stores, detected from headers.

    The file is named neutrally so detection must work off the header
    signature — naming it `<platform>.csv` would let the filename shortcut hide
    a broken signature.
    """
    csv = tmp_path / "export_download.csv"
    pd.DataFrame([PLATFORM_EXPORTS[platform]]).to_csv(csv, index=False)

    report = importer.import_csv(csv, account_id="acct1", db_path=db)

    assert report["platform"] == platform, report
    assert "error" not in report, report
    # Caption is what makes a row storable at all; without it the store drops it.
    assert "caption" in report["mapped_columns"], report
    assert "external_post_id" in report["mapped_columns"], report
    assert report["inserted"] == 1, report

    labeled = feedback_store.load_labeled(db_path=db)
    assert len(labeled) == 1
    assert labeled.iloc[0]["caption"]
    assert labeled.iloc[0]["actual_engagement_rate"] > 0


def test_importer_refuses_metrics_without_text(tmp_path, db):
    """Engagement columns but no caption and no id must error, not report zero.

    This is the failure that looked like success: every row is discarded by the
    store, and the old report said `inserted: 0` with no error at all.
    """
    csv = tmp_path / "metrics_only.csv"
    pd.DataFrame({"likes": [50], "impressions": [1000]}).to_csv(csv, index=False)

    report = importer.import_csv(csv, db_path=db)
    assert report["rows"] == 0
    assert "error" in report
    assert "caption" in report["error"]
    assert feedback_store.summary(db_path=db)["total_posts"] == 0


def test_facebook_not_detected_as_linkedin(tmp_path, db):
    """Meta writes 'Reactions' too, so detection must not key on it alone."""
    csv = tmp_path / "download.csv"
    pd.DataFrame([PLATFORM_EXPORTS["facebook"]]).to_csv(csv, index=False)
    assert importer.import_csv(csv, db_path=db)["platform"] == "facebook"


def test_ambiguous_export_still_imports_under_generic(tmp_path, db):
    """A layout no signature claims must still map, not fail.

    Meta's Instagram and Facebook exports share most of their columns, so an
    export trimmed of the distinguishing ones is genuinely ambiguous. Falling
    back to `generic` is the correct outcome: the platform label is unknown,
    but the row still carries its caption and metrics and is worth keeping.
    Detection accuracy is a convenience; losing the row would not be.
    """
    csv = tmp_path / "download.csv"
    pd.DataFrame([{
        "Post ID": "X-1", "Description": "Ambiguous but perfectly usable",
        "Reach": 900, "Likes": 40, "Comments": 3, "Shares": 1,
    }]).to_csv(csv, index=False)

    report = importer.import_csv(csv, account_id="acct1", db_path=db)
    assert report["platform"] == "generic"
    assert report["inserted"] == 1
    assert feedback_store.load_labeled(db_path=db).iloc[0]["caption"]


def test_inspect_csv_is_a_dry_run(tmp_path, db):
    """inspect_csv reports the mapping and writes nothing."""
    csv = tmp_path / "download.csv"
    pd.DataFrame([PLATFORM_EXPORTS["tiktok"]]).to_csv(csv, index=False)

    report = importer.inspect_csv(csv)
    assert report["detected_platform"] == "tiktok"
    assert report["would_import"] is True
    assert not report["missing_required"]
    assert feedback_store.summary(db_path=db)["total_posts"] == 0


def test_inspect_csv_names_the_missing_field(tmp_path):
    """An unknown layout tells the operator which alias list to extend."""
    csv = tmp_path / "download.csv"
    pd.DataFrame({"Clip headline": ["hi"], "Hearts": [5],
                  "Plays": [100]}).to_csv(csv, index=False)

    report = importer.inspect_csv(csv)
    assert report["would_import"] is False
    assert "caption" in report["missing_required"]
    assert "Clip headline" in report["unmapped_columns"]
    assert "_COLUMN_MAPS" in report["hint"]


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
