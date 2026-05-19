"""Unit tests for pure functions in the pipeline.

These tests intentionally avoid loading heavy ML models — they cover only
deterministic logic: text cleaning, feature extraction, scoring formula,
platform suitability rules, and JSON parsing.
"""

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
from generator import extract_json_from_text, standardize


# --- Text cleaning ----------------------------------------------------------

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
    row = {
        "platform": "instagram",
        "caption": "Stay fresh and hydrated naturally.",
        "hashtags": ["#eco", "#bottle", "#sustain"],
        "cta": "Shop now",
        "image_prompt": "A reusable bottle on a wooden desk with green plants nearby.",
        "shorts_prompt": "Show a young professional swapping plastic for a reusable bottle daily.",
    }
    assert platform_suitability(row) == 1.0


def test_platform_suitability_empty_email_zero_or_low():
    row = {
        "platform": "email",
        "caption": "",
        "hashtags": [],
        "cta": "",
        "image_prompt": "",
        "shorts_prompt": "",
    }
    # Email path: hashtag_count == 0 awards 1 point out of 5
    assert platform_suitability(row) == pytest.approx(0.2)


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
    out = standardize("linkedin", '{"caption": "hi"}')
    assert out["platform"] == "linkedin"
    assert out["hashtags"] == []
    assert out["cta"] == ""


def test_standardize_coerces_string_hashtags_to_list():
    out = standardize("instagram", '{"caption":"hi","hashtags":"#one"}')
    assert out["hashtags"] == ["#one"]


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
