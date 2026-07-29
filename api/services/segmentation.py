"""Module 1 as a service — segment a site's live visitors.

Pulls the behavioural features that api/routers/visitors.py derives from the
mos.js event stream, runs the hybrid engine over them, and writes the result to
the `user_segments` table (Figure 5.2 of the report).

Because a newly launched product has almost no visitors, this path spends most
of its early life in the engine's cold-start mode — which is exactly the
scenario the research is about, so the mode is reported rather than hidden.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from api import db
from api.routers.visitors import VISITOR_FEATURES_SQL
from modules.m1_segmentation.segment import MODEL_VERSION, SEGMENT_IDS, web_segmenter

log = logging.getLogger("mos.segmentation")

# Columns the web feature set needs, in the order the engine expects them.
FEATURE_COLUMNS = [
    "page_views", "clicks", "sessions", "unique_pages",
    "max_scroll_depth", "time_on_site_seconds", "form_submits", "purchases",
]


def load_visitor_features(site_id: int) -> pd.DataFrame:
    """One row per visitor, with the behavioural features Module 1 clusters on."""
    rows = db.fetch_all(VISITOR_FEATURES_SQL, site_id=site_id)
    if not rows:
        return pd.DataFrame(columns=["visitor_id", *FEATURE_COLUMNS])

    df = pd.DataFrame(rows)
    for col in FEATURE_COLUMNS:
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0.0)
    return df


def segment_site(site_id: int) -> dict[str, Any]:
    """Segment every visitor of a site and persist the labels.

    Returns a summary suitable for both the API response and the dashboard.
    """
    df = load_visitor_features(site_id)
    if df.empty:
        return {
            "site_id": site_id,
            "n_visitors": 0,
            "mode": "no_data",
            "message": "No visitors tracked yet — install the snippet and collect traffic.",
            "segments": {},
        }

    engine = web_segmenter()
    result = engine.fit_predict(df)

    rows = [
        {
            "site_id": site_id,
            "visitor_id": int(r["visitor_id"]),
            "segment_id": SEGMENT_IDS.get(r["segment_name"]),
            "segment_name": r["segment_name"],
            "segment_method": r["segment_method"],
            "segment_confidence": float(r["segment_confidence"]),
            "is_cold_start": bool(r["is_cold_start"]),
            "features": pd.Series({c: float(r[c]) for c in FEATURE_COLUMNS}).to_json(),
            "model_version": MODEL_VERSION,
        }
        for _, r in result.frame.iterrows()
    ]

    # One row per visitor: re-segmenting replaces the previous label.
    db.execute_many(
        """
        INSERT INTO user_segments (site_id, visitor_id, segment_id, segment_name,
                                   segment_method, segment_confidence, is_cold_start,
                                   features, model_version, computed_at)
        VALUES (:site_id, :visitor_id, :segment_id, :segment_name,
                :segment_method, :segment_confidence, :is_cold_start,
                CAST(:features AS jsonb), :model_version, now())
        ON CONFLICT (visitor_id) DO UPDATE SET
            segment_id         = EXCLUDED.segment_id,
            segment_name       = EXCLUDED.segment_name,
            segment_method     = EXCLUDED.segment_method,
            segment_confidence = EXCLUDED.segment_confidence,
            is_cold_start      = EXCLUDED.is_cold_start,
            features           = EXCLUDED.features,
            model_version      = EXCLUDED.model_version,
            computed_at        = now()
        """,
        rows,
    )

    diagnostics = result.diagnostics
    log.info("segmented site %s: %s visitors in %s mode",
             site_id, len(rows), diagnostics.get("mode"))

    return {
        "site_id": site_id,
        "n_visitors": len(rows),
        "mode": diagnostics.get("mode"),
        "segments": result.counts,
        "cold_start_users": diagnostics.get("cold_start_users", 0),
        "mean_confidence": diagnostics.get("mean_confidence"),
        "silhouette": diagnostics.get("silhouette"),
        "classifier_accuracy": diagnostics.get("classifier_accuracy"),
        "reason": diagnostics.get("reason"),
        "model_version": MODEL_VERSION,
    }
