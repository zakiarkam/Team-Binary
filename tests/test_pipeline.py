"""Unit tests for pure functions in the pipeline.

These tests intentionally avoid loading heavy ML models — they cover only
deterministic logic: text cleaning, feature extraction, scoring formula,
platform suitability rules, and JSON parsing.
"""

import io
import sys
from pathlib import Path

# Make project root importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import pytest

import config
from knowledge_base import _clean_text, _clean_text_list, build as build_kb
from engagement import extract_features, _count_hashtags, _count_emojis, _has_cta, _has_question
from evaluation import platform_suitability
from generator import ASSET_COLUMNS, extract_json_from_text, standardize


# --- Text cleaning ----------------------------------------------------------

dummy_summary = {
    "summary": "",
    "campaign_goal": "",
}

def test_clean_text_strips_urls_and_whitespace():
    assert _clean_text("  visit  https://example.com  now  ") == "visit  now"


def test_clean_text_collapses_whitespace():
    assert _clean_text("hello\n\tworld") == "hello world"


def test_clean_text_list_dedups_and_filters_short():
    items = ["abcd", "abcd", "ab", "    efgh    "]
    assert _clean_text_list(items, min_length=3) == ["abcd", "efgh"]


# --- Engagement feature extraction -----------------------------------------

def test_count_hashtags():
    assert _count_hashtags("hello #world #python") == 2
    assert _count_hashtags("no tags here") == 0


def test_cta_detection():
    assert _has_cta("Buy now and save") == 1
    assert _has_cta("just a thought") == 0


def test_question_hook():
    assert _has_question("Ready to upgrade?") == 1
    assert _has_question("Statement.") == 0


def test_extract_features_adds_expected_columns():
    df = pd.DataFrame({"text": ["Shop now #deal 🌱"], "platform": ["instagram"]})
    out = extract_features(df)
    for col in (
        "char_length", "word_count", "hashtag_count", "emoji_count",
        "cta_present", "question_hook", "sentiment_score", "readability_score",
    ):
        assert col in out.columns
    assert out["cta_present"].iloc[0] == 1
    assert out["hashtag_count"].iloc[0] == 1


# --- Platform suitability scoring ------------------------------------------

def test_platform_suitability_perfect_instagram():
    # Instagram is a still-image placement: a correct asset carries an image
    # prompt and no shorts prompt.
    row = {
        "platform": "instagram",
        "caption": "Stay fresh and hydrated naturally.",
        "hashtags": ["#eco", "#bottle", "#sustain"],
        "cta": "Shop now",
        "image_prompt": "A reusable bottle on a wooden desk with green plants nearby.",
        "shorts_prompt": "",
    }
    assert platform_suitability(row) == 1.0


def test_platform_suitability_penalises_wrong_creative_for_platform():
    """An image platform carrying a video prompt is not a well-formed asset."""
    base = {
        "platform": "instagram",
        "caption": "Stay fresh and hydrated naturally.",
        "hashtags": ["#eco", "#bottle", "#sustain"],
        "cta": "Shop now",
        "image_prompt": "A reusable bottle on a wooden desk with green plants nearby.",
        "shorts_prompt": "",
    }
    stray_video = {**base, "shorts_prompt": "Show someone swapping to a reusable bottle."}
    assert platform_suitability(stray_video) < platform_suitability(base)


def test_platform_suitability_perfect_shorts_needs_no_image():
    row = {
        "platform": "shorts",
        "caption": "Swap plastic for good.",
        "hashtags": ["#eco"],
        "cta": "Start today",
        "image_prompt": "",
        "shorts_prompt": "Show a commuter refilling a bottle, scene ends on the logo.",
    }
    assert platform_suitability(row) == 1.0


def test_platform_suitability_empty_email_is_low():
    row = {
        "platform": "email",
        "caption": "",
        "hashtags": [],
        "cta": "",
        "image_prompt": "",
        "shorts_prompt": "",
    }
    # Only "no hashtags" and "no stray video prompt" hold, out of six checks.
    assert platform_suitability(row) == pytest.approx(2 / 6)


def test_platform_suitability_survives_csv_round_trip():
    """Empty cells come back as NaN, which is truthy — it must not read as content."""
    row = pd.DataFrame([{
        "platform": "instagram",
        "caption": "Stay fresh and hydrated naturally.",
        "hashtags": ["#eco", "#bottle", "#sustain"],
        "cta": "Shop now",
        "image_prompt": "A reusable bottle on a wooden desk with green plants nearby.",
        "shorts_prompt": "",
    }])
    restored = pd.read_csv(io.StringIO(row.to_csv(index=False))).iloc[0]
    assert platform_suitability(restored) == 1.0


# --- Final score formula ---------------------------------------------------

def test_final_score_weights_sum_to_one():
    total = config.SEMANTIC_WEIGHT + config.PLATFORM_WEIGHT + config.ENGAGEMENT_WEIGHT
    assert total == pytest.approx(1.0)


def test_final_score_linear_combination():
    s, p, e = 1.0, 0.8, 0.5
    expected = (
        config.SEMANTIC_WEIGHT * s
        + config.PLATFORM_WEIGHT * p
        + config.ENGAGEMENT_WEIGHT * e
    )
    assert expected == pytest.approx(
        0.30 * 1.0 + 0.25 * 0.8 + 0.45 * 0.5
    )


# --- Generator JSON parsing ------------------------------------------------

def test_extract_json_from_text_handles_prose_around_json():
    raw = 'Sure, here is the JSON:\n{"platform":"x","caption":"hi"}\nThanks.'
    parsed = extract_json_from_text(raw)
    assert parsed == {"platform": "x", "caption": "hi"}


def test_extract_json_from_text_returns_none_on_garbage():
    assert extract_json_from_text("no json here at all") is None


def test_standardize_fills_missing_fields():
    out = standardize("linkedin", '{"caption": "hi"}', dummy_summary)
    assert out["platform"] == "linkedin"
    assert out["hashtags"] == []
    assert out["cta"] == ""


def test_standardize_coerces_string_hashtags_to_list():
    out = standardize("instagram", '{"caption":"hi","hashtags":"#one"}', dummy_summary)
    assert out["hashtags"] == ["#one"]


def test_standardize_keeps_only_the_creative_prompt_the_platform_uses():
    """The model may return both prompts; only the applicable one is kept."""
    both = (
        '{"caption":"hi","hashtags":["#a"],"cta":"go",'
        '"image_prompt":"a bright studio desk","shorts_prompt":"show a refill"}'
    )
    video = standardize("shorts", both, dummy_summary)
    assert video["shorts_prompt"] and not video["image_prompt"]

    still = standardize("instagram", both, dummy_summary)
    assert still["image_prompt"] and not still["shorts_prompt"]


def test_standardize_drops_hashtags_where_the_platform_has_none():
    out = standardize("email", '{"caption":"hi","hashtags":["#a","#b"]}', dummy_summary)
    assert out["hashtags"] == []


def test_standardize_caps_hashtags_at_the_platform_limit():
    tags = [f"#t{n}" for n in range(40)]
    out = standardize("instagram", '{"caption":"hi","hashtags":%s}' % str(tags).replace("'", '"'), dummy_summary)
    assert len(out["hashtags"]) == config.platform_spec("instagram")["hashtag_range"][1]


def test_standardize_always_returns_the_full_column_set():
    """Rows must stay rectangular so downstream stages can read any column."""
    out = standardize("shorts", "not json at all", dummy_summary)
    assert set(out) == set(ASSET_COLUMNS)


# --- Knowledge base build --------------------------------------------------

def test_build_kb_produces_combined_text():
    website = {
        "title": "EcoSmart Bottles",
        "meta_description": "Sustainable hydration for everyone.",
        "headings": ["Why reusable bottles matter for the planet"],
        "paragraphs": ["Our bottles are made from recycled materials and last for years."],
        "cta_texts": ["Shop now"],
        "image_alt_texts": ["bottle on desk"],
    }
    module_input = {
        "product_name": "EcoSmart Bottle",
        "target_audience": "young professionals",
        "customer_segment": "eco-conscious buyers",
    }
    kb = build_kb(website, module_input)
    assert "EcoSmart Bottle" in kb["combined_text"]
    assert "Sustainable hydration" in kb["combined_text"]
    assert kb["title"] == "EcoSmart Bottles"
