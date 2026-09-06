"""The statistics behind the report's claims.

Every "A beats B" in the write-up rests on one of these four functions, so they
are tested against cases where the right answer is known independently — not
against their own output.
"""

from __future__ import annotations

import numpy as np
import pytest

from research.stats import (Interval, bootstrap_ci, cliffs_delta,
                            describe_effect, mcnemar, paired_difference,
                            proportion_ci)


# ── Bootstrap ────────────────────────────────────────────────────────────────

def test_bootstrap_interval_brackets_the_point_estimate() -> None:
    rng = np.random.default_rng(0)
    sample = rng.normal(10, 2, 500)
    interval = bootstrap_ci(sample, lambda x: float(np.mean(x)), n_resamples=2_000)

    assert interval.low < interval.point < interval.high
    assert abs(interval.point - 10) < 0.5


def test_bootstrap_interval_narrows_as_the_sample_grows() -> None:
    """More evidence must buy a tighter interval, or the interval means nothing."""
    rng = np.random.default_rng(1)
    mean = lambda x: float(np.mean(x))  # noqa: E731

    small = bootstrap_ci(rng.normal(0, 1, 50), mean, n_resamples=2_000)
    large = bootstrap_ci(rng.normal(0, 1, 5_000), mean, n_resamples=2_000)

    assert (large.high - large.low) < (small.high - small.low)


def test_bootstrap_handles_a_sample_too_small_to_resample() -> None:
    interval = bootstrap_ci([1.0], lambda x: float(np.mean(x)))
    assert isinstance(interval, Interval)
    assert interval.method == "insufficient data"


# ── Paired comparison ────────────────────────────────────────────────────────

def test_paired_difference_detects_a_real_shift() -> None:
    rng = np.random.default_rng(2)
    base = rng.normal(0, 1, 40)
    result = paired_difference(base + 2.0, base, n_resamples=2_000)

    assert result["significant"]
    assert result["ci_low"] > 0, "an interval excluding zero is the claim"
    assert abs(result["mean_difference"] - 2.0) < 0.2


def test_paired_difference_reports_no_effect_when_there_is_none() -> None:
    rng = np.random.default_rng(3)
    a = rng.normal(0, 1, 40)
    b = rng.normal(0, 1, 40)
    result = paired_difference(a, b, n_resamples=2_000)

    assert result["ci_low"] < 0 < result["ci_high"]
    assert describe_effect(result["cliffs_delta"]) in {"negligible", "small"}


def test_paired_difference_requires_matched_series() -> None:
    with pytest.raises(ValueError):
        paired_difference([1, 2, 3], [1, 2])


# ── Effect size ──────────────────────────────────────────────────────────────

def test_cliffs_delta_is_one_when_every_value_is_larger() -> None:
    assert cliffs_delta([10, 11, 12], [1, 2, 3]) == 1.0
    assert cliffs_delta([1, 2, 3], [10, 11, 12]) == -1.0


def test_cliffs_delta_is_zero_for_identical_samples() -> None:
    assert cliffs_delta([1, 2, 3], [1, 2, 3]) == 0.0


def test_effect_size_thresholds() -> None:
    assert describe_effect(0.05) == "negligible"
    assert describe_effect(0.25) == "small"
    assert describe_effect(0.40) == "medium"
    assert describe_effect(0.90) == "large"


# ── McNemar ──────────────────────────────────────────────────────────────────

def test_mcnemar_ignores_rows_both_models_agree_on() -> None:
    """The whole point of the test: only disagreements carry information."""
    a = [True] * 50 + [True, True, False]
    b = [True] * 50 + [False, False, True]

    result = mcnemar(a, b)
    assert result["n_discordant"] == 3
    assert result["b01"] == 2 and result["b10"] == 1


def test_mcnemar_detects_a_consistent_winner() -> None:
    a = [True] * 20 + [False] * 2
    b = [False] * 20 + [True] * 2

    result = mcnemar(a, b)
    assert result["significant"]
    assert "A is right where B is wrong" in result["note"]


def test_mcnemar_reports_a_tie_without_naming_a_winner() -> None:
    """Regression: the note used to claim B won whenever the counts were equal."""
    a = [True] * 5 + [False] * 5
    b = [False] * 5 + [True] * 5

    result = mcnemar(a, b)
    assert result["b01"] == result["b10"] == 5
    assert not result["significant"]
    assert "cancel entirely" in result["note"]


def test_mcnemar_handles_identical_predictions() -> None:
    result = mcnemar([True, False, True], [True, False, True])
    assert result["p_value"] == 1.0
    assert not result["significant"]


# ── Proportions ──────────────────────────────────────────────────────────────

def test_wilson_interval_stays_inside_zero_and_one() -> None:
    """The reason Wilson is used: the normal approximation runs off the end.

    A rate of 100% is the normal state for several counts in this project, and
    an interval reaching above 1 would be nonsense.
    """
    interval = proportion_ci(20, 20)
    assert 0.0 <= interval.low <= interval.high <= 1.0
    assert interval.high == 1.0

    zero = proportion_ci(0, 20)
    assert zero.low == 0.0
    assert 0.0 <= zero.high <= 1.0


def test_wilson_interval_brackets_a_middling_proportion() -> None:
    interval = proportion_ci(50, 100)
    assert interval.low < 0.5 < interval.high


def test_proportion_of_nothing_is_not_reported_as_zero() -> None:
    interval = proportion_ci(0, 0)
    assert np.isnan(interval.point)
    assert interval.method == "no data"
