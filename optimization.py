"""Adaptive optimization: re-prompt Phi-3 with platform-specific improvement rules
and re-evaluate against the same scoring pipeline."""

import pandas as pd

import config
import engagement
import evaluation
from generator import _rules_block, _schema_block, required_fields, standardize
from models import generate_with_phi3


def _rule(row) -> str:
    p = str(row["platform"]).lower()
    s, ps, e = row["semantic_score"], row["platform_suitability_score"], row["engagement_score"]
    if s < 0.65:
        return "Keep the content closer to the original product meaning and avoid changing the business message."
    if ps < 0.75:
        return {
            "instagram": "Improve Instagram fit with a shorter caption, 3 to 5 relevant hashtags, one emoji, and a soft CTA.",
            "linkedin": "Improve LinkedIn fit with a professional tone, business value, and formal CTA.",
            # "facebook": "Improve Facebook fit with friendly wording, one clear benefit, and direct CTA.",
            "email": "Improve email fit with a subject line, concise body, clear value proposition, and no hashtags.",
            "shorts": "Improve shorts fit with a strong hook, short caption, visual scene idea, and action CTA.",
        }.get(p, "Improve clarity, engagement, and platform alignment while preserving the original product meaning.")
    if e < 0.50:
        return "Improve engagement by using clearer benefits, stronger emotional wording, and a more action-oriented CTA."
    return "Improve clarity, engagement, and platform alignment while preserving the original product meaning."


def _original_creative(row, spec: dict) -> str:
    """Show back only the creative prompt this platform uses."""
    if spec["visual"] == "image":
        return f"Original Image Prompt:\n{evaluation.as_text(row.get('image_prompt'))}"
    if spec["visual"] == "video":
        return f"Original Shorts Prompt:\n{evaluation.as_text(row.get('shorts_prompt'))}"
    return ""


def _build_prompt(row, marketing_summary: dict, rule: str) -> str:
    platform = row["platform"]
    spec = config.platform_spec(platform)
    fields = required_fields(spec)

    return f"""
You are an expert digital marketing content optimizer.

Improve this generated marketing asset.

Product Name:
{marketing_summary.get("product_name", "")}

Business Summary:
{marketing_summary.get("summary", "")}

Target Audience:
{marketing_summary.get("target_audience", "")}

Customer Segment:
{marketing_summary.get("customer_segment", "")}

Inferred Campaign Goal:
{marketing_summary.get("campaign_goal", "")}

Inferred Tone:
{marketing_summary.get("tone", "")}

Platform:
{platform}

Original Caption:
{row.get("caption", "")}

Original Hashtags:
{row.get("hashtags", "")}

Original CTA:
{row.get("cta", "")}

{_original_creative(row, spec)}

Optimization Rule:
{rule}

Return only valid JSON in this exact format:

{_schema_block(platform, fields)}

Rules:
{_rules_block(spec)}
"""


def run(ranked_df: pd.DataFrame, marketing_summary: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    optimized = []
    for _, row in ranked_df.iterrows():
        rule = _rule(row)
        raw = generate_with_phi3(_build_prompt(row, marketing_summary, rule), max_new_tokens=500)
        item = standardize(row["platform"], raw)
        item["optimization_rule"] = rule
        optimized.append(item)

    opt_df = pd.DataFrame(optimized)
    opt_df.to_csv(config.OPTIMIZED_CSV, index=False)
    print(f"Optimized assets saved → {config.OPTIMIZED_CSV}")

    opt_df = engagement.score(opt_df)
    opt_df["semantic_score"] = opt_df["caption"].apply(
        lambda c: evaluation.semantic_score(marketing_summary["summary"], c)
    )
    opt_df["platform_suitability_score"] = opt_df.apply(evaluation.platform_suitability, axis=1)
    opt_df["final_score"] = (
        config.SEMANTIC_WEIGHT * opt_df["semantic_score"]
        + config.PLATFORM_WEIGHT * opt_df["platform_suitability_score"]
        + config.ENGAGEMENT_WEIGHT * opt_df["engagement_score"]
    )
    opt_ranked = opt_df.sort_values("final_score", ascending=False).reset_index(drop=True)
    opt_ranked.to_csv(config.OPTIMIZED_RANKED_CSV, index=False)

    comparison = _build_comparison(ranked_df, opt_ranked)
    comparison.to_csv(config.COMPARISON_CSV, index=False)
    print(f"Before/after comparison saved → {config.COMPARISON_CSV}")
    print(comparison.to_string())
    return opt_ranked, comparison


def _build_comparison(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    cols = ["platform", "semantic_score", "platform_suitability_score", "engagement_score", "final_score"]
    b = before[cols].rename(
        columns={c: f"before_{c.replace('_score', '')}_score" if c != "platform" else c for c in cols}
    )
    a = after[cols].rename(
        columns={c: f"after_{c.replace('_score', '')}_score" if c != "platform" else c for c in cols}
    )
    # The original naming used "platform_score" not "platform_suitability_score"; preserve original artifact format
    b = b.rename(columns={"before_platform_suitability_score": "before_platform_score"})
    a = a.rename(columns={"after_platform_suitability_score": "after_platform_score"})

    merged = b.merge(a, on="platform", how="inner")
    merged["semantic_change"] = merged["after_semantic_score"] - merged["before_semantic_score"]
    merged["platform_change"] = merged["after_platform_score"] - merged["before_platform_score"]
    merged["engagement_change"] = merged["after_engagement_score"] - merged["before_engagement_score"]
    merged["final_score_change"] = merged["after_final_score"] - merged["before_final_score"]
    return merged


def load_cached() -> tuple[pd.DataFrame, pd.DataFrame]:
    return pd.read_csv(config.OPTIMIZED_RANKED_CSV), pd.read_csv(config.COMPARISON_CSV)
