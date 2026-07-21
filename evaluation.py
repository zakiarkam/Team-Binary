"""Semantic similarity + platform suitability + final composite score."""

import ast

import pandas as pd
from sentence_transformers import util

import config
from models import get_semantic_model


def semantic_score(source_text: str, generated_text: str) -> float:
    sm = get_semantic_model()
    src = sm.encode(str(source_text), convert_to_tensor=True)
    gen = sm.encode(str(generated_text), convert_to_tensor=True)
    return float(util.cos_sim(src, gen).item())


MIN_PROMPT_WORDS = 8


def as_text(value) -> str:
    """Read a possibly-missing cell as text.

    A CSV round-trip turns "" into NaN. NaN is truthy, so `value or ""` yields
    NaN and str() then produces the literal string "nan" — which reads as
    present content to any emptiness check.
    """
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def _as_list(value) -> list:
    """hashtags survive a CSV round-trip as a string; accept either form."""
    if isinstance(value, list):
        return value
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    text = str(value).strip()
    if not text or text in {"[]", "nan"}:
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return parsed
    except (ValueError, SyntaxError):
        pass
    return [text]


def platform_suitability(row) -> float:
    """Fraction of this platform's applicable criteria that the asset meets.

    Criteria are derived from config.PLATFORM_SPECS, so a platform is only
    judged on the creative prompt it actually needs. Scoring a platform on a
    prompt it was never asked to produce would penalise correct output.
    """
    platform = str(row["platform"]).lower()
    spec = config.platform_spec(platform)

    caption = as_text(row.get("caption"))
    cta = as_text(row.get("cta"))
    image_prompt = as_text(row.get("image_prompt"))
    shorts_prompt = as_text(row.get("shorts_prompt"))

    word_count = len(caption.split())
    hashtag_count = len(_as_list(row.get("hashtags")))

    low, high = spec["caption_words"]
    checks = [low <= word_count <= high]

    least, most = spec["hashtag_range"]
    checks.append(least <= hashtag_count <= most)

    checks.append(len(cta.strip()) > 0)

    if spec["visual"] == "image":
        checks.append(len(image_prompt.split()) >= MIN_PROMPT_WORDS)
        # A still-image placement must not carry a video prompt.
        checks.append(not shorts_prompt.strip())
    elif spec["visual"] == "video":
        checks.append(len(shorts_prompt.split()) >= MIN_PROMPT_WORDS)
        checks.append(
            "show" in shorts_prompt.lower() or "scene" in shorts_prompt.lower()
        )
        checks.append(not image_prompt.strip())

    if platform == "email":
        checks.append("subject" in caption.lower())

    return sum(bool(c) for c in checks) / len(checks)


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
