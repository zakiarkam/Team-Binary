"""Audience read API — what the dashboard shows about tracked visitors.

Everything here is derived from the raw `events` stream produced by mos.js.
The behavioural aggregates computed in `audience_summary` and `list_visitors`
are the same quantities Module 1 uses as segmentation features, so what the
dashboard displays and what the model sees can never drift apart.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api import db

router = APIRouter(tags=["audience"])

# Per-visitor behavioural features, computed from the raw event stream.
# Kept as one SQL expression block so the API and Module 1 share a definition.
VISITOR_FEATURES_SQL = """
    SELECT
        v.id                                   AS visitor_id,
        v.visitor_uid,
        v.email,
        v.name,
        v.email_consent,
        v.utm_source,
        v.device,
        v.first_seen,
        v.last_seen,
        COUNT(*) FILTER (WHERE e.event_type = 'page_view')   AS page_views,
        COUNT(*) FILTER (WHERE e.event_type = 'click')       AS clicks,
        COUNT(*) FILTER (WHERE e.event_type = 'form_submit') AS form_submits,
        COUNT(*) FILTER (WHERE e.event_type = 'purchase')    AS purchases,
        COUNT(DISTINCT e.session_id)                         AS sessions,
        COUNT(DISTINCT e.path) FILTER (WHERE e.event_type = 'page_view') AS unique_pages,
        -- Cast every derived number to float8: NUMERIC serialises to a JSON
        -- *string*, which would silently turn model features into text.
        COALESCE(MAX((e.props->>'depth')::float8)
                 FILTER (WHERE e.event_type = 'scroll'), 0)::float8  AS max_scroll_depth,
        COALESCE(SUM((e.props->>'seconds')::float8)
                 FILTER (WHERE e.event_type = 'page_exit'), 0)::float8 AS time_on_site_seconds,
        (EXTRACT(EPOCH FROM (now() - v.last_seen)) / 86400.0)::float8  AS days_since_last_seen,
        (EXTRACT(EPOCH FROM (v.last_seen - v.first_seen)) / 86400.0)::float8 AS lifetime_days
    FROM visitors v
    LEFT JOIN events e ON e.visitor_id = v.id
    WHERE v.site_id = :site_id
    GROUP BY v.id
"""


def _require_site(site_id: int) -> None:
    if db.fetch_one("SELECT 1 AS ok FROM sites WHERE id = :i", i=site_id) is None:
        raise HTTPException(404, "Site not found")


@router.get("/sites/{site_id}/audience/summary")
def audience_summary(site_id: int) -> dict:
    """Headline audience numbers plus the breakdowns the Overview page needs."""
    _require_site(site_id)

    totals = db.fetch_one(
        """
        SELECT
          COUNT(*)                                              AS visitors,
          COUNT(*) FILTER (WHERE email IS NOT NULL)             AS known,
          COUNT(*) FILTER (WHERE email_consent)                 AS reachable,
          COUNT(*) FILTER (WHERE first_seen > now() - interval '7 days')  AS new_7d,
          COUNT(*) FILTER (WHERE last_seen  > now() - interval '24 hours') AS active_24h
        FROM visitors WHERE site_id = :site_id
        """,
        site_id=site_id,
    )

    events = db.fetch_one(
        "SELECT COUNT(*) AS total FROM events WHERE site_id = :site_id",
        site_id=site_id,
    )

    by_type = db.fetch_all(
        """
        SELECT event_type, COUNT(*) AS count
        FROM events WHERE site_id = :site_id
        GROUP BY event_type ORDER BY count DESC
        """,
        site_id=site_id,
    )

    top_pages = db.fetch_all(
        """
        SELECT path, COUNT(*) AS views, COUNT(DISTINCT visitor_id) AS visitors
        FROM events
        WHERE site_id = :site_id AND event_type = 'page_view' AND path IS NOT NULL
        GROUP BY path ORDER BY views DESC LIMIT 10
        """,
        site_id=site_id,
    )

    sources = db.fetch_all(
        """
        SELECT COALESCE(utm_source, 'direct') AS source, COUNT(*) AS visitors
        FROM visitors WHERE site_id = :site_id
        GROUP BY 1 ORDER BY visitors DESC LIMIT 10
        """,
        site_id=site_id,
    )

    daily = db.fetch_all(
        """
        SELECT to_char(d.day, 'YYYY-MM-DD') AS day,
               COALESCE(COUNT(DISTINCT e.visitor_id), 0) AS visitors,
               COALESCE(COUNT(e.id), 0)                  AS events
        FROM generate_series(
                 date_trunc('day', now()) - interval '13 days',
                 date_trunc('day', now()),
                 interval '1 day') AS d(day)
        LEFT JOIN events e
               ON e.site_id = :site_id
              AND date_trunc('day', e.occurred_at) = d.day
        GROUP BY d.day ORDER BY d.day
        """,
        site_id=site_id,
    )

    segments = db.fetch_all(
        """
        SELECT segment_name, COUNT(*) AS visitors,
               -- ::float8, not ::numeric — NUMERIC serialises to a JSON string,
               -- and the dashboard then calls .toFixed() on it and crashes.
               ROUND(AVG(segment_confidence), 3)::float8 AS avg_confidence,
               COUNT(*) FILTER (WHERE is_cold_start) AS cold_start
        FROM user_segments WHERE site_id = :site_id
        GROUP BY segment_name ORDER BY visitors DESC
        """,
        site_id=site_id,
    )

    return {
        "totals": {**(totals or {}), "events": (events or {}).get("total", 0)},
        "events_by_type": by_type,
        "top_pages": top_pages,
        "sources": sources,
        "daily": daily,
        "segments": segments,
    }


@router.get("/sites/{site_id}/visitors")
def list_visitors(
    site_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    known_only: bool = False,
    reachable_only: bool = False,
    segment: str | None = None,
) -> dict:
    """Paged audience list with behavioural features and current segment."""
    _require_site(site_id)

    filters = []
    if known_only:
        filters.append("f.email IS NOT NULL")
    if reachable_only:
        filters.append("f.email_consent")
    if segment:
        filters.append("s.segment_name = :segment")
    where = f"WHERE {' AND '.join(filters)}" if filters else ""

    rows = db.fetch_all(
        f"""
        WITH f AS ({VISITOR_FEATURES_SQL})
        SELECT f.*,
               s.segment_name, s.segment_confidence::float8 AS segment_confidence,
               s.is_cold_start,
               a.predicted_conversion::float8 AS predicted_conversion,
               a.drop_off_risk::float8        AS drop_off_risk,
               a.recommendation
        FROM f
        LEFT JOIN user_segments   s ON s.visitor_id = f.visitor_id
        LEFT JOIN analytics_output a ON a.visitor_id = f.visitor_id
        {where}
        ORDER BY f.last_seen DESC
        LIMIT :limit OFFSET :offset
        """,
        site_id=site_id, limit=limit, offset=offset, segment=segment,
    )

    total = db.fetch_one(
        f"""
        WITH f AS ({VISITOR_FEATURES_SQL})
        SELECT COUNT(*) AS n
        FROM f LEFT JOIN user_segments s ON s.visitor_id = f.visitor_id
        {where}
        """,
        site_id=site_id, segment=segment,
    )

    return {
        "visitors": rows,
        "total": (total or {}).get("n", 0),
        "limit": limit,
        "offset": offset,
    }


@router.get("/visitors/{visitor_id}")
def get_visitor(visitor_id: int, events_limit: int = Query(100, ge=1, le=500)) -> dict:
    """One visitor: profile, behavioural features, segment, and their timeline."""
    visitor = db.fetch_one(
        """
        SELECT v.*, s.segment_name,
               s.segment_confidence::float8   AS segment_confidence,
               s.segment_method, s.is_cold_start,
               a.predicted_conversion::float8 AS predicted_conversion,
               a.drop_off_risk::float8        AS drop_off_risk,
               a.recommendation, a.recommended_platform
        FROM visitors v
        LEFT JOIN user_segments    s ON s.visitor_id = v.id
        LEFT JOIN analytics_output a ON a.visitor_id = v.id
        WHERE v.id = :vid
        """,
        vid=visitor_id,
    )
    if visitor is None:
        raise HTTPException(404, "Visitor not found")

    visitor.pop("ingest_secret", None)

    timeline = db.fetch_all(
        """
        SELECT event_type, path, props, occurred_at, session_id
        FROM events WHERE visitor_id = :vid
        ORDER BY occurred_at DESC LIMIT :lim
        """,
        vid=visitor_id, lim=events_limit,
    )

    return {"visitor": visitor, "timeline": timeline}
