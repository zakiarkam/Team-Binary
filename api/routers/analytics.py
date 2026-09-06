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
def recommendations(
    site_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200,
                          description="Match email or visitor id"),
    segment: str | None = None,
    recommendation: str | None = None,
) -> dict:
    """Per-customer predictions and next-best actions, highest intent first.

    Paged, searchable and filterable, because an audience of several thousand
    scored customers is not a table anyone can read top to bottom — and the row
    a marketer wants is usually a specific person, not the first fifty.
    `total` is returned so the caller can say how much it is *not* showing.
    """
    _require_site(site_id)

    filters = ["a.site_id = :s"]
    if q:
        # Bound parameter, never interpolated.
        filters.append("(v.email ILIKE :q OR v.visitor_uid ILIKE :q)")
    if segment:
        filters.append("s.segment_name = :segment")
    if recommendation:
        filters.append("a.recommendation = :rec")
    where = " AND ".join(filters)
    pattern = f"%{q.strip()}%" if q else None

    params = {"s": site_id, "q": pattern, "segment": segment,
              "rec": recommendation}

    rows = db.fetch_all(
        f"""
        -- `rank` is the customer's position among EVERYONE scored for this
        -- site, computed before the filters and paging are applied. Numbering
        -- the returned rows instead would make the first hit of any search
        -- read as the top prospect, and page two restart at 1.
        WITH ranked AS (
            SELECT visitor_id,
                   row_number() OVER (ORDER BY predicted_conversion DESC,
                                               visitor_id) AS rank
            FROM analytics_output
            WHERE site_id = :s
        )
        SELECT a.visitor_id, v.email, v.visitor_uid, s.segment_name,
               a.predicted_conversion::float8 AS predicted_conversion,
               a.drop_off_risk::float8        AS drop_off_risk,
               a.recommendation, a.recommended_platform,
               a.confidence::float8           AS confidence,
               v.source, r.rank
        FROM analytics_output a
        JOIN visitors v ON v.id = a.visitor_id
        JOIN ranked   r ON r.visitor_id = a.visitor_id
        LEFT JOIN user_segments s ON s.visitor_id = a.visitor_id
        WHERE {where}
        ORDER BY a.predicted_conversion DESC, a.visitor_id
        LIMIT :lim OFFSET :off
        """,
        **params, lim=limit, off=offset,
    )

    total = db.fetch_one(
        f"""
        SELECT count(*) AS n
        FROM analytics_output a
        JOIN visitors v ON v.id = a.visitor_id
        LEFT JOIN user_segments s ON s.visitor_id = a.visitor_id
        WHERE {where}
        """,
        **params,
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
        "total": (total or {}).get("n", 0),
        "limit": limit,
        "offset": offset,
        "query": q,
        "note": ("Ordered by predicted conversion, and `rank` is the position in "
                 "that order across the whole scored audience — not within this "
                 "page or this search. Probabilities come from models fitted on "
                 "simulated data, so treat the ranking as meaningful and the "
                 "absolute values as uncalibrated."),
    }


@router.get("/sites/{site_id}/decisions")
def decision_log(site_id: int) -> dict:
    """The append-only record of what the recommender actually decided.

    `analytics_output` holds the system's current opinion and is overwritten on
    every run. This is the history: which action was taken for whom, with what
    probability, and what followed. It is what makes the policy improvable from
    this audience rather than borrowed from another one.
    """
    _require_site(site_id)

    from api.services import decisions

    summary = decisions.summary(site_id)
    return {**summary, "off_policy": decisions.evaluate_policy(site_id)}
