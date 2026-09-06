"""attribution.py — First-touch, last-touch, linear multi-touch, and Markov-chain attribution (Phase 3).

Four models are provided:

  first_touch_attribution        — 100% credit to first platform in journey
  last_touch_attribution         — 100% credit to last pre-conversion platform
  linear_multi_touch_attribution — 1/n credit to each unique platform in journey
  markov_chain_attribution       — credit ∝ removal effect on conversion probability

Markov-chain attribution (Shao & Li 2011; Anderl et al. 2014) is the most
principled of the four: it models user journeys as transitions between
platform states plus terminal {convert, drop} states, then computes each
platform's "removal effect" — the drop in overall conversion probability
when that platform is deleted from the graph. Credits are proportional to
removal effects, normalised to 1.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

Level = Literal["platform", "channel"]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _converting_journeys(events_df: pd.DataFrame) -> pd.DataFrame:
    """Return only the pre-conversion touchpoints for users who converted.

    For each converting user, keeps all events up to (and including) their
    first convert event, sorted by timestamp. Vectorised — no per-user Python loop.
    """
    converters = events_df.loc[
        events_df["event_type"] == "convert", "user_id"
    ].unique()
    if len(converters) == 0:
        return pd.DataFrame(columns=events_df.columns)

    sub = events_df[events_df["user_id"].isin(converters)].sort_values(
        ["user_id", "timestamp"]
    ).reset_index(drop=True)
    # First-conversion timestamp per user
    first_conv = (
        sub[sub["event_type"] == "convert"]
        .groupby("user_id")["timestamp"]
        .min()
        .rename("first_conv_ts")
    )
    sub = sub.merge(first_conv, on="user_id", how="left")
    return sub[sub["timestamp"] <= sub["first_conv_ts"]].drop(columns="first_conv_ts").reset_index(drop=True)


def _normalize(series: pd.Series) -> pd.Series:
    total = series.sum()
    return (series / total).round(4) if total > 0 else series


def _credit_to_df(credit: pd.Series, level: Level) -> pd.DataFrame:
    return pd.DataFrame({level: credit.index, "credit": credit.values})


# ---------------------------------------------------------------------------
# Public attribution functions
# ---------------------------------------------------------------------------

def first_touch_attribution(
    events_df: pd.DataFrame, level: Level = "platform"
) -> pd.DataFrame:
    """Credit 100% to the first platform/channel in each converting journey."""
    journeys = _converting_journeys(events_df)
    if journeys.empty:
        return pd.DataFrame(columns=[level, "credit"])

    first_touch = (
        journeys.sort_values("timestamp")
        .groupby("user_id")[level]
        .first()
    )
    credit = _normalize(first_touch.value_counts().astype(float))
    return _credit_to_df(credit, level)


def last_touch_attribution(
    events_df: pd.DataFrame, level: Level = "platform"
) -> pd.DataFrame:
    """Credit 100% to the last platform/channel before conversion."""
    journeys = _converting_journeys(events_df)
    if journeys.empty:
        return pd.DataFrame(columns=[level, "credit"])

    # Exclude the convert event itself; last meaningful touchpoint is the one before it
    pre_convert = journeys[journeys["event_type"] != "convert"]
    if pre_convert.empty:
        pre_convert = journeys  # fallback: use the convert row

    last_touch = (
        pre_convert.sort_values("timestamp")
        .groupby("user_id")[level]
        .last()
    )
    credit = _normalize(last_touch.value_counts().astype(float))
    return _credit_to_df(credit, level)


def linear_multi_touch_attribution(
    events_df: pd.DataFrame, level: Level = "platform"
) -> pd.DataFrame:
    """Divide credit equally among all unique platforms/channels in each converting journey."""
    journeys = _converting_journeys(events_df)
    if journeys.empty:
        return pd.DataFrame(columns=[level, "credit"])

    raw_credits: dict[str, float] = {}

    for uid, grp in journeys.groupby("user_id"):
        unique_touches = grp[level].unique()
        share = 1.0 / len(unique_touches)
        for touch in unique_touches:
            raw_credits[touch] = raw_credits.get(touch, 0.0) + share

    credit = _normalize(pd.Series(raw_credits).sort_values(ascending=False))
    return _credit_to_df(credit, level)


# ---------------------------------------------------------------------------
# Markov-chain attribution (removal-effect method)
# ---------------------------------------------------------------------------

_START = "<START>"
_CONV = "<CONVERT>"
_DROP = "<DROP>"


def _build_journeys(events_df: pd.DataFrame, level: Level) -> list[tuple[list[str], bool]]:
    """Return [(platform_sequence, converted)] per user. Drops pure 'sent' noise.

    Vectorised: sort once, group once, build sequences via list aggregation.
    """
    meaningful = events_df[events_df["event_type"].isin({"open", "click", "convert"})]
    if meaningful.empty:
        return []
    meaningful = meaningful.sort_values("timestamp")
    grouped = meaningful.groupby("user_id", sort=False).agg(
        seq=(level, list),
        events=("event_type", set),
    )
    journeys: list[tuple[list[str], bool]] = []
    for seq, events in zip(grouped["seq"], grouped["events"]):
        if seq:
            journeys.append((seq, "convert" in events))
    return journeys


def _transition_matrix(
    journeys: list[tuple[list[str], bool]],
    states: list[str],
) -> dict[str, dict[str, float]]:
    """Build a first-order transition matrix over states ∪ {START, CONVERT, DROP}."""
    nodes = [_START] + list(states) + [_CONV, _DROP]
    counts = {s: {t: 0.0 for t in nodes} for s in nodes}

    for seq, converted in journeys:
        prev = _START
        for s in seq:
            counts[prev][s] += 1
            prev = s
        terminal = _CONV if converted else _DROP
        counts[prev][terminal] += 1

    probs = {s: {t: 0.0 for t in nodes} for s in nodes}
    for s, row in counts.items():
        total = sum(row.values())
        if total > 0:
            for t, c in row.items():
                probs[s][t] = c / total
    # Absorbing states
    probs[_CONV][_CONV] = 1.0
    probs[_DROP][_DROP] = 1.0
    return probs


def _absorption_prob(
    probs: dict[str, dict[str, float]],
    states: list[str],
    removed: str | None = None,
) -> float:
    """P(eventually reach CONVERT starting from START). If `removed` is set,
    redistribute that state's outgoing mass to DROP before solving."""
    nodes = [_START] + list(states) + [_CONV, _DROP]

    # Build transition matrix copy with removal
    P = {s: dict(probs[s]) for s in nodes}
    if removed is not None and removed in P:
        # Force the removed node into DROP (no flow through it).
        for s in nodes:
            P[s][removed], leak = 0.0, P[s][removed]
            P[s][_DROP] += leak
        # And from the removed node itself, send everything to DROP.
        for t in P[removed]:
            P[removed][t] = 0.0
        P[removed][_DROP] = 1.0

    # Solve via iteration: f(s) = P(reach CONVERT | start in s)
    f = {s: 0.0 for s in nodes}
    f[_CONV] = 1.0
    f[_DROP] = 0.0
    for _ in range(200):  # converges fast for this small graph
        new_f = dict(f)
        for s in nodes:
            if s in (_CONV, _DROP):
                continue
            new_f[s] = sum(P[s][t] * f[t] for t in nodes)
        if max(abs(new_f[s] - f[s]) for s in nodes) < 1e-9:
            f = new_f
            break
        f = new_f
    return f[_START]


def markov_chain_attribution(
    events_df: pd.DataFrame, level: Level = "platform"
) -> pd.DataFrame:
    """First-order Markov-chain attribution using the removal-effect method.

    For each platform p, compute the conversion probability of the journey
    graph with p removed; the platform's credit is proportional to the drop
    (the "removal effect"). This rewards platforms whose deletion would most
    damage conversions.
    """
    journeys = _build_journeys(events_df, level)
    if not journeys:
        return pd.DataFrame(columns=[level, "credit"])

    states = sorted({s for seq, _ in journeys for s in seq})
    probs = _transition_matrix(journeys, states)
    base_conv = _absorption_prob(probs, states)
    if base_conv <= 0:
        return pd.DataFrame({level: states, "credit": [1.0 / len(states)] * len(states)})

    removal_effects: dict[str, float] = {}
    for s in states:
        without = _absorption_prob(probs, states, removed=s)
        removal_effects[s] = max(0.0, base_conv - without)

    series = pd.Series(removal_effects)
    credit = _normalize(series.sort_values(ascending=False))
    return _credit_to_df(credit, level)


# ---------------------------------------------------------------------------
# Research comparison: model credits vs ground truth
# ---------------------------------------------------------------------------

def compare_to_ground_truth(
    events_df: pd.DataFrame,
    ground_truth_df: pd.DataFrame,
    level: Level = "platform",
) -> pd.DataFrame:
    """Return a DataFrame with model credits and MAE vs ground truth per model.

    ground_truth_df must have columns [platform, true_influence].
    Returns columns: platform, true_influence, first_touch, last_touch,
                     multi_touch, markov, ae_*.
    """
    models = {
        "first_touch":  first_touch_attribution(events_df, level),
        "last_touch":   last_touch_attribution(events_df, level),
        "multi_touch":  linear_multi_touch_attribution(events_df, level),
        "markov":       markov_chain_attribution(events_df, level),
    }

    result = ground_truth_df.copy().rename(columns={level: level})
    for name, df in models.items():
        merged = df.rename(columns={"credit": name})
        result = result.merge(merged, on=level, how="left")
        result[name] = result[name].fillna(0.0)

    for name in models:
        result[f"ae_{name}"] = (result[name] - result["true_influence"]).abs()

    return result


def attribution_mae(comparison_df: pd.DataFrame) -> dict[str, float]:
    """Return mean absolute error per attribution model from compare_to_ground_truth output."""
    out = {
        "first_touch": round(comparison_df["ae_first_touch"].mean(), 4),
        "last_touch":  round(comparison_df["ae_last_touch"].mean(), 4),
        "multi_touch": round(comparison_df["ae_multi_touch"].mean(), 4),
    }
    if "ae_markov" in comparison_df.columns:
        out["markov"] = round(comparison_df["ae_markov"].mean(), 4)
    return out
