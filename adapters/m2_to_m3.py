"""Adapter: Module 2 (automation) outputs -> Module 3 (analytics) inputs.

Module 2 writes a WIDE event log — one row per message with boolean flags:
    user_id, message_index, sent, opened, clicked, converted, triggered,
    timestamp_day, segment_name, strategy      (email-only, no platform)

Module 3 consumes a LONG event log — one row per event:
    user_id, timestamp, channel, platform, campaign_id, strategy, event_type
    event_type in {sent, open, click, convert}

Module 2 models generic email campaigns, so every real M2 event is mapped to
platform="email", channel="email". This is honest: no multi-platform journeys
are invented (see INTEGRATION_PLAN.md §5, option C — M3's multi-platform
attribution study runs on M3's own simulator; M2's real data feeds the funnel
and conversion analytics, which do not require multiple platforms).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from .segment_labels import to_snake

# Anchor so synthesized timestamps are deterministic and human-readable.
REFERENCE_DATE = datetime(2026, 5, 1, 12, 0, 0)

# Matches Module 3's funnel.STAGES exactly.
STAGES = ["sent", "open", "click", "convert"]

_FLAG_TO_EVENT = [
    ("sent", "sent"),
    ("opened", "open"),
    ("clicked", "click"),
    ("converted", "convert"),
]


def wide_to_long(m2_events: pd.DataFrame) -> pd.DataFrame:
    """Explode M2 wide event rows into M3 long event rows."""
    rows: list[dict] = []
    for r in m2_events.itertuples(index=False):
        day = int(getattr(r, "timestamp_day", getattr(r, "message_index", 0)))
        ts = (REFERENCE_DATE + timedelta(days=day)).isoformat()
        strategy = getattr(r, "strategy", "fixed")
        base = {
            "user_id": getattr(r, "user_id"),
            "timestamp": ts,
            "channel": "email",
            "platform": "email",
            "campaign_id": f"email_{strategy}_v1",
            "strategy": strategy,
        }
        for flag, event_type in _FLAG_TO_EVENT:
            if bool(getattr(r, flag)):
                rows.append({**base, "event_type": event_type})
    long_df = pd.DataFrame(rows, columns=[
        "user_id", "timestamp", "channel", "platform",
        "campaign_id", "strategy", "event_type",
    ])
    return long_df


def funnel_from_wide(m2_events: pd.DataFrame) -> dict[str, int]:
    """Unique users reaching each funnel stage, computed on the WIDE frame.

    Identical semantics to Module 3's funnel.compute_funnel, but reads the
    boolean columns directly (no explode needed).
    """
    flag_col = {"sent": "sent", "open": "opened", "click": "clicked", "convert": "converted"}
    out: dict[str, int] = {}
    for stage in STAGES:
        col = flag_col[stage]
        out[stage] = int(m2_events.loc[m2_events[col] == True, "user_id"].nunique())  # noqa: E712
    return out


def dropoffs(funnel: dict[str, int]) -> dict[str, float]:
    """Drop-off rate (0-1) between consecutive stages. Mirrors M3.compute_dropoffs."""
    transitions = [("sent→open", "sent", "open"),
                   ("open→click", "open", "click"),
                   ("click→convert", "click", "convert")]
    out: dict[str, float] = {}
    for label, a, b in transitions:
        denom = funnel.get(a, 0)
        out[label] = round(1 - funnel.get(b, 0) / denom, 4) if denom else 0.0
    return out


def funnel_by_strategy(m2_events: pd.DataFrame) -> pd.DataFrame:
    """Funnel counts per automation strategy (real M2 data)."""
    rows = []
    for strat, g in m2_events.groupby("strategy"):
        row = {"strategy": strat}
        row.update(funnel_from_wide(g))
        rows.append(row)
    return pd.DataFrame(rows).set_index("strategy")


def segments_to_m3(m1_segments: pd.DataFrame) -> pd.DataFrame:
    """M1 user_segments -> M3 segment schema (user_id, segment, confidence)."""
    df = m1_segments.copy()
    uid = "CustomerID" if "CustomerID" in df.columns else "user_id"
    conf_col = "segment_confidence" if "segment_confidence" in df.columns else None
    out = pd.DataFrame({
        "user_id": df[uid],
        "segment": df["segment_name"].map(to_snake),
        "confidence": df[conf_col] if conf_col else 0.8,
    })
    return out
