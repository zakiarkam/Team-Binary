"""Decision rules shared with Module 3's recommender.

These delegate to `modules/m3_analytics/src/recommender.py` so the production
system and the research report cannot drift apart. The local copies exist only
as a fallback for when Module 3 cannot be imported (its package expects to be
imported from its own root), and they are byte-for-byte the same rules.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

M3_DIR = Path(__file__).resolve().parents[2] / "modules" / "m3_analytics"


def _m3_recommender():
    if str(M3_DIR) not in sys.path:
        sys.path.insert(0, str(M3_DIR))
    from src import recommender  # type: ignore
    return recommender


def next_best_action(p_conv: float, p_drop: float, segment: str) -> str:
    """Which campaign action this visitor should receive next."""
    try:
        return _m3_recommender()._recommendation(p_conv, p_drop, segment)
    except Exception:
        if p_conv >= 0.7:
            return "send_premium_offer"
        if p_drop >= 0.6 and segment == "price_sensitive":
            return "send_reactivation_campaign"
        if p_conv >= 0.3:
            return "send_personalized_offer"
        return "send_general_reminder"


#: Share of the audience eligible for each tier, strongest action first. The
#: numbers are a budget, not a discovered truth: a marketer can only make so
#: many premium offers, and the point of ranking is to spend that budget on the
#: customers most likely to justify it.
TOP_TIER_SHARE = 0.10
SECOND_TIER_SHARE = 0.30

#: The cold-start segment never receives the strongest action. That segment
#: exists precisely because there is not enough evidence about these people, and
#: the most aggressive treatment is the one that most needs evidence behind it.
COLD_START_SEGMENTS = {"new_cold_customer", "new_cold_user"}


def rank_based_actions(p_conv, p_drop, segments) -> list[str]:
    """Choose each customer's next action by their *rank*, not by a threshold.

    Why this exists, and why it differs from `next_best_action`
    ----------------------------------------------------------
    Module 3's rule applies absolute cut-offs — `p_conv >= 0.7` earns a premium
    offer. Those cut-offs were calibrated on the distribution the models were
    fitted on. Applied to a different audience they stop meaning anything:
    experiment E5 measured predicted conversion on the imported research
    audience and found a median of 0.95 for two segments, so the 0.7 cut-off
    fired for 64% of everybody and the "premium" offer stopped being selective.
    E5's own recommendation is to rank rather than threshold, and this is that
    recommendation applied.

    Ranking is invariant to any monotone distortion of the probabilities, which
    is exactly the distortion a transfer across distributions produces. The
    model's *ordering* survives the move; its calibration does not.

    Module 3's absolute rule is deliberately left unchanged — it is a published
    research artifact, and E8 compares the two policies.
    """
    conv = np.asarray(p_conv, dtype=float)
    drop = np.asarray(p_drop, dtype=float)
    labels = [str(s or "") for s in segments]
    n = len(conv)
    if n == 0:
        return []

    # Percentile rank within this audience: 1.0 is the most likely to convert.
    # `average` breaks ties evenly, which matters because a transferred model
    # often assigns whole segments an identical score.
    conv_rank = pd.Series(conv).rank(pct=True, method="average").to_numpy()
    drop_rank = pd.Series(drop).rank(pct=True, method="average").to_numpy()

    actions = []
    for i in range(n):
        cold = labels[i] in COLD_START_SEGMENTS

        if drop_rank[i] >= 1.0 - TOP_TIER_SHARE and conv_rank[i] < 0.5:
            # About to leave and unlikely to buy unaided — win them back first.
            actions.append("send_reactivation_campaign")
        elif conv_rank[i] >= 1.0 - TOP_TIER_SHARE and not cold:
            actions.append("send_premium_offer")
        elif conv_rank[i] >= 1.0 - SECOND_TIER_SHARE:
            actions.append("send_personalized_offer")
        elif cold:
            # Someone we know almost nothing about: introduce the product
            # rather than discount it.
            actions.append("send_personalized_offer")
        else:
            actions.append("send_general_reminder")
    return actions


def confidence(p_conv: float, p_drop: float) -> float:
    """How decisive the model was — distance from an even 50/50 call."""
    try:
        return _m3_recommender()._confidence(p_conv, p_drop)
    except Exception:
        return round(max(abs(p_conv - 0.5), abs(p_drop - 0.5)) + 0.5, 4)


def heuristic_scores(feature_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Transparent fallback for when the trained models cannot be loaded.

    Deliberately simple and monotonic — more engagement means more conversion
    likelihood and less drop-off risk. It exists so the pipeline degrades to
    something explainable instead of failing, and any output that uses it is
    labelled as a fallback rather than presented as a model prediction.
    """
    opens = pd.to_numeric(feature_df.get("n_opens", 0), errors="coerce").fillna(0)
    clicks = pd.to_numeric(feature_df.get("n_clicks", 0), errors="coerce").fillna(0)
    recency = pd.to_numeric(feature_df.get("recency_days", 0), errors="coerce").fillna(0)

    engagement = (opens * 0.15 + clicks * 0.35).clip(0, 1)
    staleness = (recency / 30.0).clip(0, 1)

    p_conv = (engagement * (1 - 0.4 * staleness)).clip(0.01, 0.99)
    p_drop = (1 - engagement) * (0.5 + 0.5 * staleness)
    return p_conv.to_numpy(), p_drop.clip(0.01, 0.99).to_numpy()
