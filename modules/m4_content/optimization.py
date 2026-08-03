"""
Adaptive optimization stage.

Flow:

ranked_platform_assets.csv
        |
        | input hash check
        v
Optimize with Phi-3
        |
        v
Re-score engagement
        |
        v
Evaluate semantic/platform score
        |
        v
Save optimized artifacts
"""

from __future__ import annotations

import pandas as pd

import config
import engagement
import evaluation

from generator import (
    _rules_block,
    _schema_block,
    required_fields,
    standardize,
)

from models import generate_with_phi3


# ---------------------------------------------------------
# Optimization rules
# ---------------------------------------------------------

def _rule(row) -> str:

    semantic = float(row["semantic_score"])
    platform_score = float(row["platform_suitability_score"])
    engagement_score = float(row["engagement_score"])

    platform = str(row["platform"]).lower()


    if semantic < 0.65:
        return (
            "Keep the content closer to the original product meaning "
            "and avoid changing the business message."
        )


    if platform_score < 0.75:

        return {
            "instagram":
                (
                    "Improve Instagram fit with a stronger hook, "
                    "shorter caption, relevant hashtags and soft CTA."
                ),

            "linkedin":
                (
                    "Improve LinkedIn fit with professional wording, "
                    "business insight and formal CTA."
                ),

            "email":
                (
                    "Improve email fit with strong subject line, "
                    "clear value proposition and no hashtags."
                ),

            "shorts":
                (
                    "Improve short video fit with a strong first-second "
                    "hook and clear visual storytelling."
                ),

            # tiktok is in config.PLATFORMS and facebook in SERVICE_PLATFORMS,
            # but neither had a rule here, so the two of them were the only
            # channels told merely to "improve clarity" — the least actionable
            # advice, given to the platforms with the most specific conventions.
            "tiktok":
                (
                    "Improve TikTok fit with a first-second hook, spoken-word "
                    "phrasing, a very short caption and 3-5 native hashtags."
                ),

            "facebook":
                (
                    "Improve Facebook fit with a conversational opening, plain "
                    "wording, few hashtags and a CTA that invites a reply."
                ),

        }.get(
            platform,
            "Improve clarity, engagement and platform alignment."
        )


    if engagement_score < 0.50:

        return (
            "Improve engagement using stronger emotional wording, "
            "clear benefits and action-oriented CTA."
        )


    return (
        "Improve clarity, engagement and platform alignment "
        "while preserving the original meaning."
    )



# ---------------------------------------------------------
# Creative prompt recovery
# ---------------------------------------------------------

def _original_creative(row, spec):

    visual = spec.get(
        "visual",
        spec.get(
            "default_visual",
            "image"
        )
    )


    if visual == "image":

        return (
            "Original Image Prompt:\n"
            f"{evaluation.as_text(row.get('image_prompt'))}"
        )


    if visual == "video":

        return (
            "Original Video Prompt:\n"
            f"{evaluation.as_text(row.get('shorts_prompt'))}"
        )


    return ""


# ---------------------------------------------------------
# Phi-3 optimization prompt
# ---------------------------------------------------------

def _build_prompt(row, marketing_summary, rule):

    platform = row["platform"]

    spec = config.platform_spec(platform)

    fields = required_fields(spec)

    # Re-prompting has to target the same register the asset was generated in,
    # or optimization quietly rewrites a TikTok caption back into the brand's
    # LinkedIn voice. Same rule as generator.build_prompt.
    brand_tone = marketing_summary.get("tone", "")

    tone_for_platform = config.platform_tone(
        platform,
        brand_tone,
    )


    return f"""

You are an expert marketing content optimizer.

Improve the following generated marketing asset.

Product:
{marketing_summary.get("product_name","")}


Business Summary:
{marketing_summary.get("summary","")}


Audience:
{marketing_summary.get("target_audience","")}


Customer Segment:
{marketing_summary.get("customer_segment","")}


Campaign Goal:
{marketing_summary.get("campaign_goal","")}


Brand Voice:
{brand_tone}


Tone for this platform:
{tone_for_platform}


How this platform is spoken:
{config.register_note(platform)}


Platform:
{platform}


Current Caption:

{row.get("caption","")}


Current Hashtags:

{row.get("hashtags","")}


Current CTA:

{row.get("cta","")}


{_original_creative(row,spec)}


Optimization Instruction:

{rule}


Return only JSON:

{_schema_block(platform,fields)}


Rules:

{_rules_block(spec, tone_for_platform)}

"""



# ---------------------------------------------------------
# Main optimization stage
# ---------------------------------------------------------

def run(
    ranked_df: pd.DataFrame,
    marketing_summary: dict
) -> tuple[pd.DataFrame,pd.DataFrame]:

    optimized_rows = []


    rows = list(
        ranked_df.iterrows()
    )


    for index, (_, row) in enumerate(
        rows,
        start=1
    ):


        rule = _rule(row)


        print(
            f"\n--- [{index}/{len(rows)}] "
            f"Optimizing {row['platform'].upper()} ---"
        )


        raw = generate_with_phi3(
            _build_prompt(
                row,
                marketing_summary,
                rule,
            ),
            max_new_tokens=500,
        )


        item = standardize(
            row["platform"],
            raw,
            marketing_summary,
        )


        item["optimization_rule"] = rule


        optimized_rows.append(item)



    optimized_df = pd.DataFrame(
        optimized_rows
    )



    optimized_df.to_csv(
        config.OPTIMIZED_CSV,
        index=False,
    )


    print(
        f"Optimized assets saved → "
        f"{config.OPTIMIZED_CSV}"
    )



    # -----------------------------
    # Re-score optimized content
    # -----------------------------


    optimized_df = engagement.score(
        optimized_df
    )


    optimized_df["semantic_score"] = (
        optimized_df["caption"]
        .apply(
            lambda x:
            evaluation.semantic_score(
                marketing_summary["summary"],
                x,
            )
        )
    )


    optimized_df[
        "platform_suitability_score"
    ] = optimized_df.apply(
        evaluation.platform_suitability,
        axis=1,
    )


    optimized_df["final_score"] = (

        config.SEMANTIC_WEIGHT
        *
        optimized_df["semantic_score"]

        +

        config.PLATFORM_WEIGHT
        *
        optimized_df[
            "platform_suitability_score"
        ]

        +

        config.ENGAGEMENT_WEIGHT
        *
        optimized_df["engagement_score"]

    )



    optimized_ranked = (
        optimized_df
        .sort_values(
            "final_score",
            ascending=False,
        )
        .reset_index(drop=True)
    )



    optimized_ranked.to_csv(
        config.OPTIMIZED_RANKED_CSV,
        index=False,
    )



    comparison = _build_comparison(
        ranked_df,
        optimized_ranked,
    )


    comparison.to_csv(
        config.COMPARISON_CSV,
        index=False,
    )

    print(
        f"Comparison saved → {config.COMPARISON_CSV}"
    )


    return (
        optimized_ranked,
        comparison,
    )



# ---------------------------------------------------------
# Comparison report
# ---------------------------------------------------------

def _build_comparison(
    before,
    after
):

    cols = [
        "platform",
        "semantic_score",
        "platform_suitability_score",
        "engagement_score",
        "final_score",
    ]


    before_df = (
        before[cols]
        .rename(
            columns={
                c:
                f"before_{c}"
                for c in cols
                if c != "platform"
            }
        )
    )


    after_df = (
        after[cols]
        .rename(
            columns={
                c:
                f"after_{c}"
                for c in cols
                if c != "platform"
            }
        )
    )



    merged = before_df.merge(
        after_df,
        on="platform",
        how="inner",
    )



    merged["semantic_change"] = (
        merged["after_semantic_score"]
        -
        merged["before_semantic_score"]
    )


    merged["platform_change"] = (
        merged["after_platform_suitability_score"]
        -
        merged["before_platform_suitability_score"]
    )


    merged["engagement_change"] = (
        merged["after_engagement_score"]
        -
        merged["before_engagement_score"]
    )


    merged["final_score_change"] = (
        merged["after_final_score"]
        -
        merged["before_final_score"]
    )


    return merged



# ---------------------------------------------------------
# Cache loader
# ---------------------------------------------------------

def load_cached():

    return (

        pd.read_csv(
            config.OPTIMIZED_RANKED_CSV
        ),

        pd.read_csv(
            config.COMPARISON_CSV
        ),

    )