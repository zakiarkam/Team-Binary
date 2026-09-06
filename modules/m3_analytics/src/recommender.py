"""recommender.py — Per-user decision support and system-level insights (Phase 6)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from src.attribution import (
    first_touch_attribution,
    last_touch_attribution,
    linear_multi_touch_attribution,
)
from src.features import build_features
from src.funnel import compute_dropoffs, funnel_by
from src.prediction import FEATURES, MODEL_COL

# Global fallback for cold-start users (no engagement events)
_GLOBAL_BEST_PLATFORM = "linkedin"   # highest ground-truth influence


# ---------------------------------------------------------------------------
# Per-user credit helpers
# ---------------------------------------------------------------------------

def _per_user_credits(events_df: pd.DataFrame) -> dict[str, dict]:
    """Return {user_id: {"platform_credits": {...}, "channel_credits": {...}}} for every user."""
    result: dict[str, dict] = {}
    for uid, grp in events_df.groupby("user_id"):
        if grp.empty:
            result[uid] = {
                "platform_credits": {},
                "channel_credits":  {},
                "best_platform":    _GLOBAL_BEST_PLATFORM,
            }
            continue

        plat_counts = grp["platform"].value_counts()
        chan_counts  = grp["channel"].value_counts()

        plat_total = plat_counts.sum()
        chan_total  = chan_counts.sum()

        platform_credits = {p: round(float(c) / plat_total, 4)
                            for p, c in plat_counts.items()}
        channel_credits  = {c: round(float(v) / chan_total, 4)
                            for c, v in chan_counts.items()}

        # Renormalise to exactly 1.0 (avoid rounding drift)
        _renorm(platform_credits)
        _renorm(channel_credits)

        best_platform = max(platform_credits, key=platform_credits.get)
        result[uid] = {
            "platform_credits": platform_credits,
            "channel_credits":  channel_credits,
            "best_platform":    best_platform,
        }
    return result


def _renorm(d: dict[str, float]) -> None:
    total = sum(d.values())
    if total > 0:
        for k in d:
            d[k] = round(d[k] / total, 4)


# ---------------------------------------------------------------------------
# Recommendation rule engine
# ---------------------------------------------------------------------------

def _recommendation(p_conv: float, p_drop: float, segment: str) -> str:
    if p_conv >= 0.7:
        return "send_premium_offer"
    if p_drop >= 0.6 and segment == "price_sensitive":
        return "send_reactivation_campaign"
    if p_conv >= 0.3:
        return "send_personalized_offer"
    return "send_general_reminder"


def _confidence(p_conv: float, p_drop: float) -> float:
    """Confidence = how decisive the model is (distance from 0.5)."""
    return round(max(abs(p_conv - 0.5), abs(p_drop - 0.5)) + 0.5, 4)


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------

def build_recommendations(
    events_df: pd.DataFrame,
    segments_df: pd.DataFrame,
    models_dir: Path,
) -> list[dict]:
    """Return the per-user analytics output list (schema §5.3)."""
    features_df = build_features(events_df, segments_df)

    conv_pipe = joblib.load(models_dir / "conversion_xgboost.pkl")
    drop_pipe  = joblib.load(models_dir / "drop_off_xgboost.pkl")

    p_conv = conv_pipe.predict_proba(features_df[FEATURES])[:, 1]
    p_drop = drop_pipe.predict_proba(features_df[FEATURES])[:, 1]

    credits = _per_user_credits(events_df)

    records = []
    for i, row in features_df.iterrows():
        uid  = row["user_id"]
        pc   = float(p_conv[i])
        pd_  = float(p_drop[i])
        seg  = row["segment"]

        user_credits = credits.get(uid, {
            "platform_credits": {}, "channel_credits": {}, "best_platform": _GLOBAL_BEST_PLATFORM
        })
        best_plat = user_credits["best_platform"] or _GLOBAL_BEST_PLATFORM

        rec = _recommendation(pc, pd_, seg)

        records.append({
            "user_id":               uid,
            "modality":              "analytics",
            "predicted_conversion":  round(pc, 4),
            "drop_off_risk":         round(pd_, 4),
            "attribution_model":     "multi_touch",
            "channel_credits":       user_credits["channel_credits"],
            "platform_credits":      user_credits["platform_credits"],
            "best_platform":         best_plat,
            "recommendation":        rec,
            "recommended_platform":  best_plat,
            "confidence":            _confidence(pc, pd_),
        })

    return records


# ---------------------------------------------------------------------------
# System-level insight strings
# ---------------------------------------------------------------------------

def build_insights(events_df: pd.DataFrame, segments_df: pd.DataFrame) -> list[str]:
    """Generate human-readable system-level insight strings."""
    insights: list[str] = []

    # 1. Segment with highest click→convert drop-off
    events_seg = events_df.merge(
        segments_df[["user_id", "segment"]], on="user_id", how="left"
    )
    seg_funnel = funnel_by(events_seg, by="segment")
    worst_seg, worst_rate = None, -1.0
    for seg, row in seg_funnel.iterrows():
        funnel_dict = {"sent": row["sent"], "open": row["open"],
                       "click": row["click"], "convert": row["convert"]}
        do = compute_dropoffs(funnel_dict)
        rate = do.get("click→convert", 0.0)
        if rate > worst_rate:
            worst_rate, worst_seg = rate, seg
    insights.append(
        f"Drop-off between click and convert is highest for segment "
        f"'{worst_seg}' ({worst_rate * 100:.1f}%)."
    )

    # 2. First-touch vs last-touch: find platform with biggest credit shift
    ft = first_touch_attribution(events_df, level="platform").set_index("platform")["credit"]
    lt = last_touch_attribution(events_df, level="platform").set_index("platform")["credit"]
    all_plats = ft.index.union(lt.index)
    ft = ft.reindex(all_plats, fill_value=0.0)
    lt = lt.reindex(all_plats, fill_value=0.0)
    shift = (lt - ft)                          # positive = gains in last-touch
    gainer  = shift.idxmax()                   # platform that gains most last-touch credit
    loser   = shift.idxmin()                   # platform that loses most last-touch credit
    insights.append(
        f"{loser.capitalize()} leads first-touch ({ft[loser]*100:.1f}%) but loses credit "
        f"in last-touch, while {gainer.capitalize()} gains the most last-touch credit "
        f"({lt[gainer]*100:.1f}%) — use {loser.capitalize()} for acquisition, "
        f"{gainer.capitalize()} for closing."
    )

    # 3. Trigger vs fixed conversion lift
    strategies = {}
    for strat, grp in events_df.groupby("strategy"):
        funnel_dict = {
            et: grp.loc[grp["event_type"] == et, "user_id"].nunique()
            for et in ["sent", "open", "click", "convert"]
        }
        strategies[strat] = (
            funnel_dict["convert"] / funnel_dict["sent"]
            if funnel_dict["sent"] else 0
        )

    if "trigger" in strategies and "fixed" in strategies and strategies["fixed"] > 0:
        lift = (strategies["trigger"] - strategies["fixed"]) / strategies["fixed"] * 100
        insights.append(
            f"Trigger strategy yields {lift:.1f}% higher conversion rate than fixed "
            f"({strategies['trigger'] * 100:.1f}% vs {strategies['fixed'] * 100:.1f}%)."
        )

    # 4. Best-performing segment overall
    seg_funnel["conv_rate"] = seg_funnel["convert"] / seg_funnel["sent"].replace(0, float("nan"))
    best_seg = seg_funnel["conv_rate"].idxmax()
    best_rate = seg_funnel.loc[best_seg, "conv_rate"]
    insights.append(
        f"'{best_seg}' is the highest-converting segment "
        f"({best_rate * 100:.1f}% end-to-end conversion rate)."
    )

    return insights


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_output(records: list[dict]) -> None:
    """Raise AssertionError if any record violates the §5.3 schema."""
    required_keys = {
        "user_id", "modality", "predicted_conversion", "drop_off_risk",
        "attribution_model", "channel_credits", "platform_credits",
        "best_platform", "recommendation", "recommended_platform", "confidence",
    }
    valid_recs = {
        "send_premium_offer", "send_reactivation_campaign",
        "send_personalized_offer", "send_general_reminder",
    }
    for r in records:
        assert required_keys.issubset(r.keys()), f"Missing keys in record for {r.get('user_id')}"
        assert r["modality"] == "analytics"
        assert 0 <= r["predicted_conversion"] <= 1
        assert 0 <= r["drop_off_risk"] <= 1
        assert r["recommendation"] in valid_recs
        if r["channel_credits"]:
            total = sum(r["channel_credits"].values())
            assert abs(total - 1.0) < 0.02, f"channel_credits sum={total} for {r['user_id']}"
        if r["platform_credits"]:
            total = sum(r["platform_credits"].values())
            assert abs(total - 1.0) < 0.02, f"platform_credits sum={total} for {r['user_id']}"


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate per-user analytics output.")
    parser.add_argument("--out", default="outputs/reports/analytics_output.json")
    parser.add_argument("--simulated-dir", default="data/simulated/")
    parser.add_argument("--models-dir",    default="outputs/models/")
    args = parser.parse_args()

    sim_dir   = Path(args.simulated_dir)
    mdl_dir   = Path(args.models_dir)
    out_path  = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    events   = pd.read_csv(sim_dir / "event_logs.csv",   parse_dates=["timestamp"])
    segments = pd.read_csv(sim_dir / "user_segments.csv")

    print("Building per-user recommendations...")
    records = build_recommendations(events, segments, mdl_dir)
    validate_output(records)

    with open(out_path, "w") as f:
        json.dump(records, f, indent=2)
    print(f"Saved {len(records)} records → {out_path}")

    # Recommendation breakdown
    from collections import Counter
    counts = Counter(r["recommendation"] for r in records)
    for rec, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {rec:<35} {n:>5} users ({n/len(records)*100:.1f}%)")

    # Insights
    print("\nGenerating system-level insights...")
    insights = build_insights(events, segments)
    insights_path = out_path.parent / "insights.md"
    with open(insights_path, "w") as f:
        f.write("# System-Level Marketing Insights\n\n")
        for ins in insights:
            f.write(f"- {ins}\n")
    print(f"Saved {len(insights)} insights → {insights_path}")
    for ins in insights:
        print(f"  • {ins}")


if __name__ == "__main__":
    main()
