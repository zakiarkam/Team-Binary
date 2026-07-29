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
