"""Semantic similarity + platform suitability + final composite score."""

import pandas as pd
from sentence_transformers import util

import config
from models import get_semantic_model


def semantic_score(source_text: str, generated_text: str) -> float:
    sm = get_semantic_model()
    src = sm.encode(str(source_text), convert_to_tensor=True)
    gen = sm.encode(str(generated_text), convert_to_tensor=True)
    return float(util.cos_sim(src, gen).item())


def platform_suitability(row) -> float:
    platform = str(row["platform"]).lower()
    caption = str(row["caption"])
    hashtags = row["hashtags"] if isinstance(row["hashtags"], list) else [row["hashtags"]] if row["hashtags"] else []
    cta = str(row["cta"])
    image_prompt = str(row["image_prompt"])
    shorts_prompt = str(row["shorts_prompt"])

    word_count = len(caption.split())
    hashtag_count = len(hashtags)
    has_cta = len(cta.strip()) > 0
    has_image_prompt = len(image_prompt.split()) >= 8
    has_shorts_prompt = len(shorts_prompt.split()) >= 8

    score = 0
    max_score = 5

    if platform == "instagram":
        if word_count <= 40: score += 1
        if hashtag_count >= 3: score += 1
        if has_cta: score += 1
        if has_image_prompt: score += 1
        if has_shorts_prompt: score += 1
    elif platform == "linkedin":
        if word_count >= 20: score += 1
        if hashtag_count <= 5: score += 1
        if has_cta: score += 1
        if has_image_prompt: score += 1
        if has_shorts_prompt: score += 1
    elif platform == "facebook":
        if word_count <= 80: score += 1
        if hashtag_count <= 5: score += 1
        if has_cta: score += 1
        if has_image_prompt: score += 1
        if has_shorts_prompt: score += 1
    elif platform == "email":
        if "subject" in caption.lower() or word_count >= 20: score += 1
        if hashtag_count == 0: score += 1
        if has_cta: score += 1
        if has_image_prompt: score += 1
        if has_shorts_prompt: score += 1
    elif platform == "shorts":
        if word_count <= 30: score += 1
        if has_cta: score += 1
        if has_image_prompt: score += 1
        if has_shorts_prompt: score += 1
        if "show" in shorts_prompt.lower() or "scene" in shorts_prompt.lower(): score += 1
    else:
        if word_count <= 80: score += 1
        if has_cta: score += 1
        if has_image_prompt: score += 1
        if has_shorts_prompt: score += 1
        if hashtag_count <= 5: score += 1

    return score / max_score


def run(generated_assets_df: pd.DataFrame, marketing_summary: dict) -> pd.DataFrame:
    """Adds semantic_score, platform_suitability_score, final_score and ranks."""
    src = marketing_summary["summary"]
    generated_assets_df["semantic_score"] = generated_assets_df["caption"].apply(
        lambda c: semantic_score(src, c)
    )
    generated_assets_df["platform_suitability_score"] = generated_assets_df.apply(
        platform_suitability, axis=1
    )
    generated_assets_df["final_score"] = (
        config.SEMANTIC_WEIGHT * generated_assets_df["semantic_score"]
        + config.PLATFORM_WEIGHT * generated_assets_df["platform_suitability_score"]
        + config.ENGAGEMENT_WEIGHT * generated_assets_df["engagement_score"]
    )
    ranked = generated_assets_df.sort_values("final_score", ascending=False).reset_index(drop=True)
    ranked.to_csv(config.RANKED_CSV, index=False)
    print(f"Ranked assets saved → {config.RANKED_CSV}")
    print(ranked[["platform", "semantic_score", "platform_suitability_score",
                  "engagement_score", "final_score"]].to_string())
    return ranked


def load_cached() -> pd.DataFrame:
    return pd.read_csv(config.RANKED_CSV)
