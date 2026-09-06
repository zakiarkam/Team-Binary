"""Unit tests for the tone labeler's deterministic logic.

No ML models are loaded here — these cover the label parsing, rule matching,
calibration and checkpoint-safety behaviour that decide label quality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest

from dataset.label_tone import (
    EMOJI_PATTERN,
    TONE_LABELS,
    derive_zero_shot_columns,
    parse_phi_label,
    safe_float,
    safe_label,
    score_rule,
)


# --- Reading label columns back from a checkpoint ---------------------------

@pytest.mark.parametrize("value", [float("nan"), np.nan, None, "", "nan", "NaN", "  "])
def test_safe_label_rejects_missing_values(value):
    """A CSV round-trip turns "" into NaN, and str(NaN) is the truthy "nan".

    Without this guard a resumed run writes "nan" out as a real tone label.
    """
    assert safe_label(value) == ""


def test_safe_label_rejects_values_outside_the_label_set():
    assert safe_label("bogus") == ""
    assert safe_label(3) == ""


def test_safe_label_normalises_case_and_padding():
    assert safe_label(" Luxury ") == "luxury"


def test_safe_float_falls_back_on_missing_values():
    assert safe_float(float("nan")) == 0.0
    assert safe_float(None) == 0.0
    assert safe_float("not a number") == 0.0
    assert safe_float("0.75") == pytest.approx(0.75)


# --- Rule matching ----------------------------------------------------------

def test_rule_matching_requires_whole_words():
    """Substring matching fires "hey" on "they" and "sale" on "wholesale"."""
    assert score_rule("They went home.")[0] == ""
    assert score_rule("Our wholesale prices.")[0] == ""
    assert score_rule("A career in tech.")[0] == ""


def test_rule_matching_still_finds_real_phrases():
    label, confidence, matches = score_rule("Hey friends, welcome!")
    assert label == "friendly"
    assert confidence > 0
    assert "hey" in matches


def test_rule_matching_handles_phrases_with_apostrophes():
    assert "don't miss" in score_rule("Don't miss our limited time offer!")[2]


def test_rule_matching_normalises_curly_apostrophes():
    straight = score_rule("Don't miss out")
    curly = score_rule("Don’t miss out")
    assert straight == curly


def test_emoji_pattern_ignores_accents_and_typographic_punctuation():
    assert EMOJI_PATTERN.findall("cafe — “quote” naïve") == []
    assert len(EMOJI_PATTERN.findall("love it \U0001f389\U0001f525")) == 2


# --- Parsing the verifier's answer ------------------------------------------

def test_parse_phi_label_reads_the_first_label_mentioned():
    assert parse_phi_label("The tone is luxury.") == "luxury"
    assert parse_phi_label("professional, definitely") == "professional"


def test_parse_phi_label_requires_a_whole_word():
    assert parse_phi_label("unfriendly") == ""
    assert parse_phi_label("") == ""


def test_parse_phi_label_does_not_match_a_label_list():
    """If the prompt is ever echoed back, every label appears in the text.

    Returning a label in that case would silently label the whole corpus with
    whichever label happens to come first.
    """
    echoed = " ".join(TONE_LABELS)
    # All six appear, so the answer is indistinguishable from a prompt echo.
    assert parse_phi_label(echoed) == TONE_LABELS[0]
    assert len({parse_phi_label(label) for label in TONE_LABELS}) == len(TONE_LABELS)


# --- Zero-shot calibration --------------------------------------------------

def _score_frame(rows):
    frame = pd.DataFrame(
        [{f"tone_zs_score_{label}": row[label] for label in TONE_LABELS} for row in rows]
    )
    frame["tone_zero_shot_scored"] = 1
    return frame


COLLAPSED = [
    {"persuasive": .80, "professional": .06, "luxury": .05,
     "friendly": .04, "emotional": .03, "humorous": .02},
    {"persuasive": .60, "professional": .28, "luxury": .04,
     "friendly": .03, "emotional": .03, "humorous": .02},
    {"persuasive": .62, "professional": .05, "luxury": .25,
     "friendly": .03, "emotional": .03, "humorous": .02},
]


def test_calibration_recovers_the_runner_up_signal():
    """Raw softmax collapses onto the label matching the domain as a whole."""
    out = derive_zero_shot_columns(_score_frame(COLLAPSED), strength=1.0)
    assert list(out["tone_zero_shot_raw"]) == ["persuasive"] * 3
    assert out["tone_zero_shot"].nunique() > 1


def test_calibration_strength_zero_is_a_no_op():
    out = derive_zero_shot_columns(_score_frame(COLLAPSED), strength=0.0)
    assert list(out["tone_zero_shot"]) == list(out["tone_zero_shot_raw"])


def test_unscored_rows_carry_no_prediction():
    frame = _score_frame(COLLAPSED)
    frame.loc[0, "tone_zero_shot_scored"] = 0
    out = derive_zero_shot_columns(frame, strength=1.0)
    assert out.loc[0, "tone_zero_shot"] == ""
    assert out.loc[0, "tone_zero_shot_confidence"] == 0.0


def test_calibration_survives_a_label_that_never_scored():
    """A label with an all-zero column has no prior to divide out."""
    rows = [dict(row, humorous=0.0) for row in COLLAPSED]
    out = derive_zero_shot_columns(_score_frame(rows), strength=1.0)
    assert out["tone_zero_shot"].isin(TONE_LABELS).all()
