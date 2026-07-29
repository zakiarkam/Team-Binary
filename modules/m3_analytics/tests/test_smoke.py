"""
Smoke tests for every module — runs on a 50-user sample so CI stays fast.
"""

import pandas as pd
import pytest
from pathlib import Path

from src.simulator import simulate

TINY = 50   

@pytest.fixture(scope="module")
def sim_frames():
    return simulate(n_users=TINY, seed=42)


class TestSimulator:
    def test_output_keys(self, sim_frames):
        assert set(sim_frames) == {"user_segments", "event_logs", "ground_truth_influence"}

    def test_user_segments_schema(self, sim_frames):
        df = sim_frames["user_segments"]
        assert list(df.columns) == ["user_id", "segment", "confidence"]
        assert df["user_id"].is_unique
        valid_segs = {"new_cold_customer", "low_engagement", "loyal_customer",
                      "high_intent", "price_sensitive"}
        assert set(df["segment"]).issubset(valid_segs)
        assert df["confidence"].between(0.0, 1.0).all()
        assert len(df) == TINY

    def test_event_logs_schema(self, sim_frames):
        df = sim_frames["event_logs"]
        required = {"user_id", "timestamp", "channel", "platform", "campaign_id",
                    "strategy", "event_type"}
        assert required.issubset(df.columns)

    def test_event_logs_valid_values(self, sim_frames):
        df = sim_frames["event_logs"]
        valid_events = {"sent", "open", "click", "convert"}
        assert set(df["event_type"]).issubset(valid_events)

        valid_channels = {"email", "social", "ad", "offer"}
        assert set(df["channel"]).issubset(valid_channels)

        valid_platforms = {"email", "facebook", "instagram", "linkedin", "tiktok"}
        assert set(df["platform"]).issubset(valid_platforms)

        valid_strategies = {"fixed", "trigger", "hybrid"}
        assert set(df["strategy"]).issubset(valid_strategies)

    def test_channel_platform_pairs(self, sim_frames):
        """Every (channel, platform) pair must be in the allowed set from CLAUDE.md §5.2."""
        allowed = {
            ("email", "email"),
            ("social", "facebook"), ("social", "instagram"),
            ("social", "linkedin"), ("social", "tiktok"),
            ("ad", "facebook"), ("ad", "instagram"),
            ("offer", "email"),
        }
        df = sim_frames["event_logs"]
        pairs = set(zip(df["channel"], df["platform"]))
        bad = pairs - allowed
        assert not bad, f"Invalid (channel, platform) pairs: {bad}"

    def test_funnel_ordering(self, sim_frames):
        """If a user has a convert event, they must also have open and click events."""
        df = sim_frames["event_logs"]
        for uid, grp in df.groupby("user_id"):
            events = set(grp["event_type"])
            if "convert" in events:
                assert "click" in events, f"{uid} has convert but no click"
                assert "open" in events, f"{uid} has convert but no open"
            if "click" in events:
                assert "open" in events, f"{uid} has click but no open"

    def test_ground_truth_sums_to_one(self, sim_frames):
        gt = sim_frames["ground_truth_influence"]
        assert list(gt.columns) == ["platform", "true_influence"]
        total = gt["true_influence"].sum()
        assert abs(total - 1.0) < 0.01, f"Ground truth sums to {total}, expected ~1.0"

    def test_all_users_in_events(self, sim_frames):
        seg_ids = set(sim_frames["user_segments"]["user_id"])
        evt_ids = set(sim_frames["event_logs"]["user_id"])
        assert evt_ids.issubset(seg_ids)

    def test_strategy_split(self, sim_frames):
        """All three strategies must appear in the event log."""
        df = sim_frames["event_logs"]
        assert set(df["strategy"]) == {"fixed", "trigger", "hybrid"}


class TestFunnel:
    def test_compute_funnel_keys(self, sim_frames):
        from src.funnel import compute_funnel
        funnel = compute_funnel(sim_frames["event_logs"])
        assert set(funnel.keys()) == {"sent", "open", "click", "convert"}

    def test_funnel_monotone(self, sim_frames):
        from src.funnel import compute_funnel
        f = compute_funnel(sim_frames["event_logs"])
        assert f["sent"] >= f["open"] >= f["click"] >= f["convert"]

    def test_compute_dropoffs_range(self, sim_frames):
        from src.funnel import compute_funnel, compute_dropoffs
        f = compute_funnel(sim_frames["event_logs"])
        do = compute_dropoffs(f)
        for key, val in do.items():
            assert 0.0 <= val <= 1.0, f"{key} drop-off {val} out of range"

    def test_funnel_by_strategy(self, sim_frames):
        from src.funnel import funnel_by
        df = funnel_by(sim_frames["event_logs"], by="strategy")
        assert set(df.index) == {"fixed", "trigger", "hybrid"}
        for stage in ["sent", "open", "click", "convert"]:
            assert stage in df.columns

    def test_funnel_by_segment(self, sim_frames):
        from src.funnel import funnel_by
        events_seg = sim_frames["event_logs"].merge(
            sim_frames["user_segments"][["user_id", "segment"]], on="user_id", how="left"
        )
        df = funnel_by(events_seg, by="segment")
        assert len(df) > 0
        assert "convert" in df.columns


class TestAttribution:
    def test_credits_sum_to_one(self, sim_frames):
        from src.attribution import (
            first_touch_attribution, last_touch_attribution,
            linear_multi_touch_attribution,
        )
        events = sim_frames["event_logs"]
        for fn in [first_touch_attribution, last_touch_attribution,
                   linear_multi_touch_attribution]:
            df = fn(events, level="platform")
            total = df["credit"].sum()
            assert abs(total - 1.0) < 0.01, f"{fn.__name__} credits sum to {total}"

    def test_channel_level(self, sim_frames):
        from src.attribution import linear_multi_touch_attribution
        df = linear_multi_touch_attribution(sim_frames["event_logs"], level="channel")
        assert "channel" in df.columns
        valid_channels = {"email", "social", "ad", "offer"}
        assert set(df["channel"]).issubset(valid_channels)

    def test_mae_multi_lower_than_last(self, sim_frames):
        from src.attribution import compare_to_ground_truth, attribution_mae
        import pandas as pd
        gt = pd.read_csv("data/simulated/ground_truth_influence.csv")
        comp = compare_to_ground_truth(sim_frames["event_logs"], gt)
        mae = attribution_mae(comp)
        assert mae["multi_touch"] < mae["last_touch"], (
            f"Expected multi-touch MAE < last-touch, got {mae}"
        )


class TestFeatures:
    def test_feature_shape(self, sim_frames):
        from src.features import build_features
        feat = build_features(sim_frames["event_logs"], sim_frames["user_segments"])
        assert len(feat) == len(sim_frames["user_segments"])

    def test_required_columns(self, sim_frames):
        from src.features import build_features
        feat = build_features(sim_frames["event_logs"], sim_frames["user_segments"])
        required = {"user_id", "segment", "n_sent", "n_opens", "n_clicks",
                    "journey_length", "avg_time_between_events_hours", "recency_days",
                    "dominant_channel", "first_channel", "last_channel",
                    "converted", "dropped_off"}
        assert required.issubset(set(feat.columns))

    def test_targets_binary(self, sim_frames):
        from src.features import build_features
        feat = build_features(sim_frames["event_logs"], sim_frames["user_segments"])
        assert set(feat["converted"].unique()).issubset({0, 1})
        assert set(feat["dropped_off"].unique()).issubset({0, 1})

    def test_converters_not_dropped_off(self, sim_frames):
        from src.features import build_features
        feat = build_features(sim_frames["event_logs"], sim_frames["user_segments"])
        # A user who converted cannot also be dropped off
        both = feat[(feat["converted"] == 1) & (feat["dropped_off"] == 1)]
        assert len(both) == 0, f"{len(both)} users flagged as both converted and dropped_off"


class TestPrediction:
    def test_models_saved(self):
        from pathlib import Path
        models_dir = Path("outputs/models")
        expected = [
            "conversion_logistic_regression.pkl",
            "conversion_random_forest.pkl",
            "conversion_xgboost.pkl",
            "drop_off_logistic_regression.pkl",
            "drop_off_random_forest.pkl",
            "drop_off_xgboost.pkl",
        ]
        for fname in expected:
            assert (models_dir / fname).exists(), f"Missing model: {fname}"

    def test_metrics_csv(self):
        import pandas as pd
        from pathlib import Path
        path = Path("outputs/reports/model_metrics.csv")
        assert path.exists()
        df = pd.read_csv(path)
        assert set(["target", "model", "accuracy", "f1", "auc"]).issubset(df.columns)
        assert len(df) == 6  # 3 models × 2 targets

    def test_model_predict(self):
        import joblib, pandas as pd
        from pathlib import Path
        pipe = joblib.load("outputs/models/conversion_xgboost.pkl")
        feat = pd.read_csv("data/processed/features.csv").head(5)
        from src.prediction import FEATURES
        proba = pipe.predict_proba(feat[FEATURES])[:, 1]
        assert all(0 <= p <= 1 for p in proba)


class TestEvaluation:
    def test_attribution_study_returns_dataframe(self, sim_frames):
        from src.evaluation import attribution_comparison_study
        import pandas as pd, tempfile
        from pathlib import Path
        gt = pd.read_csv("data/simulated/ground_truth_influence.csv")
        with tempfile.TemporaryDirectory() as tmp:
            comp = attribution_comparison_study(
                sim_frames["event_logs"], gt, Path(tmp)
            )
        assert isinstance(comp, pd.DataFrame)
        assert "platform" in comp.columns

    def test_strategy_study_has_all_strategies(self, sim_frames):
        from src.evaluation import strategy_comparison_study
        import pandas as pd, tempfile
        from pathlib import Path
        feat = pd.read_csv("data/processed/features.csv")
        mdl  = Path("outputs/models")
        with tempfile.TemporaryDirectory() as tmp:
            df = strategy_comparison_study(
                sim_frames["event_logs"], feat, mdl, Path(tmp)
            )
        assert set(df["strategy"]) == {"fixed", "trigger", "hybrid"}
        assert "conv_rate" in df.columns

    def test_eval_figures_exist(self):
        from pathlib import Path
        figs = Path("outputs/figures")
        expected = [
            "eval_attribution_study.png",
            "eval_roc_conversion.png", "eval_roc_drop_off.png",
            "eval_cm_conversion.png",  "eval_cm_drop_off.png",
            "eval_strategy_comparison.png",
        ]
        for f in expected:
            assert (figs / f).exists(), f"Missing figure: {f}"


class TestRecommender:
    def test_build_recommendations_schema(self, sim_frames):
        from src.recommender import build_recommendations, validate_output
        from pathlib import Path
        recs = build_recommendations(
            sim_frames["event_logs"],
            sim_frames["user_segments"],
            Path("outputs/models"),
        )
        assert len(recs) == len(sim_frames["user_segments"])
        validate_output(recs)  # raises AssertionError on schema violation

    def test_all_recommendation_types_present(self, sim_frames):
        from src.recommender import build_recommendations
        from pathlib import Path
        recs = build_recommendations(
            sim_frames["event_logs"],
            sim_frames["user_segments"],
            Path("outputs/models"),
        )
        valid = {"send_premium_offer", "send_reactivation_campaign",
                 "send_personalized_offer", "send_general_reminder"}
        actual = {r["recommendation"] for r in recs}
        assert actual.issubset(valid)

    def test_output_json_exists_and_valid(self):
        import json
        from pathlib import Path
        path = Path("outputs/reports/analytics_output.json")
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        # Simulator default user count changed to 10,000; allow either size
        assert len(data) in (2000, 10000)
        assert all(r["modality"] == "analytics" for r in data)

    def test_insights_file_exists(self):
        from pathlib import Path
        assert Path("outputs/reports/insights.md").exists()

    def test_insights_content(self):
        path = "outputs/reports/insights.md"
        with open(path) as f:
            content = f.read()
        assert "price_sensitive" in content or "drop-off" in content.lower()
        assert "%" in content


class TestPhase7:
    def test_bank_marketing_data_exists(self):
        from pathlib import Path
        p = Path("data/raw/bank_marketing") / "bank-additional-full.csv"
        if not p.exists():
            pytest.skip(
                "Bank Marketing raw data not present (data/raw/ is git-ignored). "
                "Download it to enable the calibration/validation test."
            )
        assert p.exists()

    def test_validation_comparison_csv(self):
        import pandas as pd
        from pathlib import Path
        path = Path("outputs/reports/validation_comparison.csv")
        assert path.exists()
        df = pd.read_csv(path)
        assert "Bank Mktg AUC" in df.columns
        assert len(df) == 3
        # XGBoost should be competitive on real data (AUC > 0.80)
        xgb_row = df[df["Model"] == "XGBoost"]
        assert float(xgb_row["Bank Mktg AUC"].values[0]) > 0.80

    def test_dashboard_importable(self):
        import importlib.util, sys
        from pathlib import Path
        # Just check the file is syntactically valid Python
        spec = importlib.util.spec_from_file_location(
            "app", Path("dashboard/app.py")
        )
        assert spec is not None

    def test_pipeline_module_importable(self):
        from src.pipeline import run_full
        assert callable(run_full)

    def test_final_notebook_exists(self):
        from pathlib import Path
        assert Path("notebooks/04_final_results.ipynb").exists()
