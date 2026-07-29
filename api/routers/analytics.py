"""Analytics endpoints — Module 3 over observed campaign data."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api import db
from api.services import analytics as svc

router = APIRouter(tags=["analytics"])


def _require_site(site_id: int) -> None:
    if db.fetch_one("SELECT 1 AS ok FROM sites WHERE id = :i", i=site_id) is None:
        raise HTTPException(404, "Site not found")


@router.get("/sites/{site_id}/analytics/funnel")
def funnel(site_id: int) -> dict:
    """Campaign funnel and drop-off, sliced by strategy and by segment."""
    _require_site(site_id)
    return svc.build_funnel(site_id)


@router.get("/sites/{site_id}/analytics/attribution")
def attribution(
    site_id: int,
    level: str = Query("platform", pattern="^(platform|channel)$"),
) -> dict:
    """First-touch, last-touch, linear and Markov attribution side by side."""
    _require_site(site_id)
    return svc.build_attribution(site_id, level=level)


@router.post("/sites/{site_id}/analytics/run")
def run(site_id: int) -> dict:
    """Full analytics pass: funnel, attribution, predictions, insights.

    Writes per-visitor predictions to `analytics_output`, which is what closes
    the loop back into campaigns (Module 2) and content (Module 4).
    """
    _require_site(site_id)
    try:
        return svc.run_analytics(site_id)
    except Exception as exc:
        db.execute(
            """INSERT INTO pipeline_runs (site_id, stage, status, error, finished_at)
               VALUES (:s, 'analytics', 'failed', :e, now())""",
            s=site_id, e=str(exc)[:2000])
        raise HTTPException(500, f"Analytics failed: {exc}") from exc


@router.get("/sites/{site_id}/analytics/recommendations")
def recommendations(site_id: int, limit: int = Query(50, ge=1, le=500)) -> dict:
    """Per-visitor predictions and next-best actions, highest intent first."""
    _require_site(site_id)

    rows = db.fetch_all(
        """
        SELECT a.visitor_id, v.email, s.segment_name,
               a.predicted_conversion::float8 AS predicted_conversion,
               a.drop_off_risk::float8        AS drop_off_risk,
               a.recommendation, a.recommended_platform,
               a.confidence::float8           AS confidence,
               v.source
        FROM analytics_output a
        JOIN visitors v ON v.id = a.visitor_id
        LEFT JOIN user_segments s ON s.visitor_id = a.visitor_id
        WHERE a.site_id = :s
        ORDER BY a.predicted_conversion DESC
        LIMIT :lim
        """,
        s=site_id, lim=limit,
    )

    mix = db.fetch_all(
        """SELECT recommendation, count(*) AS visitors
           FROM analytics_output WHERE site_id = :s
           GROUP BY 1 ORDER BY visitors DESC""",
        s=site_id,
    )

    return {
        "recommendations": rows,
        "mix": mix,
        "note": ("Ordered by predicted conversion. Probabilities come from models "
                 "fitted on simulated data, so treat the ranking as meaningful and "
                 "the absolute values as uncalibrated."),
    }
