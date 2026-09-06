"""Statistics used to defend the claims in the report.

Every headline number in this project should come with an interval, and every
"A beats B" should come with a test. This module is small on purpose: four
tools, each chosen because it makes the fewest assumptions the data can violate.

Why these and not the textbook defaults
---------------------------------------
*   **Percentile bootstrap** rather than a normal-theory interval. Conversion
    separation, silhouette and macro-F1 are not means and have no closed-form
    standard error; resampling makes no distributional claim at all.
*   **Paired bootstrap / Wilcoxon** rather than an unpaired t-test when
    comparing policies. Each simulation seed produces the *same* users under
    all three policies, so the runs are paired and the pairing removes most of
    the between-run variance. Ignoring it wastes power and overstates p.
*   **Exact McNemar** rather than chi-square when comparing two classifiers on
    one test set. The models see identical rows, so the only informative cells
    are the disagreements, and with a few hundred rows the exact binomial is
    right where the asymptotic approximation is not.
*   **Cliff's delta** alongside p-values. With 30 seeds almost anything reaches
    significance; the effect size is what says whether it matters.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Sequence

import numpy as np

from research.config import N_BOOTSTRAP, SEED


@dataclass(frozen=True)
class Interval:
    """A point estimate with a confidence interval."""

    point: float
    low: float
    high: float
    method: str = "percentile bootstrap"
    level: float = 0.95

    def __str__(self) -> str:
        return f"{self.point:.4g} [{self.low:.4g}, {self.high:.4g}]"

    def as_dict(self) -> dict:
        return asdict(self)


def bootstrap_ci(
    data: np.ndarray | Sequence,
    statistic: Callable[[np.ndarray], float],
    n_resamples: int = N_BOOTSTRAP,
    level: float = 0.95,
    seed: int = SEED,
) -> Interval:
    """Percentile bootstrap CI for any statistic of a one-dimensional sample.

    `data` may be an array of values or an array of row *indices* into a larger
    frame — resampling indices is how the segment-separation statistic, which
    needs several columns at once, is bootstrapped.
    """
    values = np.asarray(data)
    n = len(values)
    if n < 2:
        point = float(statistic(values)) if n else float("nan")
        return Interval(point, float("nan"), float("nan"), "insufficient data", level)

    rng = np.random.default_rng(seed)
    point = float(statistic(values))

    draws = np.empty(n_resamples)
    for i in range(n_resamples):
        draws[i] = statistic(values[rng.integers(0, n, n)])

    draws = draws[np.isfinite(draws)]
    if draws.size == 0:                                   # pragma: no cover
        return Interval(point, float("nan"), float("nan"), "degenerate", level)

    alpha = (1.0 - level) / 2.0
    return Interval(point,
                    float(np.quantile(draws, alpha)),
                    float(np.quantile(draws, 1.0 - alpha)),
                    "percentile bootstrap", level)


def paired_difference(
    a: Sequence[float],
    b: Sequence[float],
    level: float = 0.95,
    seed: int = SEED,
    n_resamples: int = N_BOOTSTRAP,
) -> dict:
    """Compare two paired series — e.g. one policy against another, seed by seed.

    Returns the mean difference with a bootstrap CI, the Wilcoxon signed-rank
    p-value, and Cliff's delta. An interval that excludes zero and a delta above
    ~0.15 is the pair of facts worth reporting; either alone is weak.
    """
    x, y = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if x.shape != y.shape:
        raise ValueError("paired_difference needs two series of equal length")

    diff = x - y
    interval = bootstrap_ci(diff, lambda d: float(np.mean(d)),
                            n_resamples=n_resamples, level=level, seed=seed)

    p_value = float("nan")
    if len(diff) >= 6 and np.any(diff != 0):
        from scipy.stats import wilcoxon
        try:
            p_value = float(wilcoxon(x, y, zero_method="wilcox").pvalue)
        except ValueError:                                # all differences zero
            p_value = 1.0

    return {
        "mean_difference": interval.point,
        "ci_low": interval.low,
        "ci_high": interval.high,
        "wilcoxon_p": p_value,
        "cliffs_delta": cliffs_delta(x, y),
        "n_pairs": int(len(diff)),
        "significant": bool(np.isfinite(p_value) and p_value < 0.05),
    }


def cliffs_delta(a: Sequence[float], b: Sequence[float]) -> float:
    """Non-parametric effect size in [-1, 1]: P(a > b) − P(a < b).

    Interpretation thresholds in common use: |δ| < 0.147 negligible,
    < 0.33 small, < 0.474 medium, else large.
    """
    x, y = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if x.size == 0 or y.size == 0:
        return float("nan")
    # Broadcast comparison: fine at these sizes and avoids a Python loop.
    greater = int(np.sum(x[:, None] > y[None, :]))
    less = int(np.sum(x[:, None] < y[None, :]))
    return float((greater - less) / (x.size * y.size))


def mcnemar(correct_a: Sequence[bool], correct_b: Sequence[bool]) -> dict:
    """Exact McNemar test for two classifiers scored on the same rows.

    Only the disagreements carry information: `b01` is where A was right and B
    wrong, `b10` the reverse. Rows both got right or both got wrong say nothing
    about which model is better, which is precisely why a plain accuracy
    difference on a small test set is so easy to over-read.
    """
    a = np.asarray(correct_a, dtype=bool)
    b = np.asarray(correct_b, dtype=bool)
    if a.shape != b.shape:
        raise ValueError("mcnemar needs two score vectors of equal length")

    b01 = int(np.sum(a & ~b))
    b10 = int(np.sum(~a & b))
    n_discordant = b01 + b10

    if n_discordant == 0:
        return {"b01": 0, "b10": 0, "n_discordant": 0, "p_value": 1.0,
                "significant": False,
                "note": "the two models made identical predictions on every row"}

    from scipy.stats import binomtest
    p = float(binomtest(b01, n_discordant, 0.5).pvalue)

    if b01 == b10:
        note = (f"each model is right where the other is wrong exactly {b01} "
                "times — the disagreements cancel entirely")
    elif b01 > b10:
        note = "A is right where B is wrong more often than the reverse"
    else:
        note = "B is right where A is wrong more often than the reverse"

    return {
        "b01": b01, "b10": b10, "n_discordant": n_discordant,
        "p_value": p, "significant": bool(p < 0.05), "note": note,
    }


def proportion_ci(successes: int, total: int, level: float = 0.95) -> Interval:
    """Wilson score interval for a proportion.

    Preferred over the normal approximation because it stays inside [0, 1] and
    keeps its coverage when the proportion is near 0 or 1 — which is exactly
    where this project's rates live (a 2% conversion, a 95% consent rate).
    """
    if total <= 0:
        return Interval(float("nan"), float("nan"), float("nan"), "no data", level)

    from scipy.stats import norm

    z = float(norm.ppf(1 - (1 - level) / 2))
    p = successes / total
    denom = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denom
    half = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denom
    return Interval(float(p), float(max(0.0, centre - half)),
                    float(min(1.0, centre + half)), "Wilson score", level)


def describe_effect(delta: float) -> str:
    """Plain-language size for a Cliff's delta, for the results tables."""
    d = abs(delta)
    if not np.isfinite(d):
        return "unknown"
    if d < 0.147:
        return "negligible"
    if d < 0.33:
        return "small"
    if d < 0.474:
        return "medium"
    return "large"
