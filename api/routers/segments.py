"""Segmentation endpoints — run Module 1 over a site's tracked visitors."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api import db
from api.services import segmentation

router = APIRouter(tags=["segmentation"])


def _require_site(site_id: int) -> None:
    if db.fetch_one("SELECT 1 AS ok FROM sites WHERE id = :i", i=site_id) is None:
        raise HTTPException(404, "Site not found")


@router.post("/sites/{site_id}/segment")
def run_segmentation(site_id: int) -> dict:
    """Re-segment the whole audience and store the result.

    Safe to call repeatedly: each visitor keeps exactly one current segment.
    """
    _require_site(site_id)

    run = db.fetch_one(
        """
        INSERT INTO pipeline_runs (site_id, stage, status)
        VALUES (:site_id, 'segmentation', 'running') RETURNING id
        """,
        site_id=site_id,
    )
    run_id = run["id"] if run else None

    try:
        summary = segmentation.segment_site(site_id)
    except Exception as exc:
        db.execute(
            """UPDATE pipeline_runs SET status='failed', error=:err, finished_at=now()
               WHERE id=:id""",
            id=run_id, err=str(exc)[:2000],
        )
        raise HTTPException(500, f"Segmentation failed: {exc}") from exc

    db.execute(
        """UPDATE pipeline_runs SET status='ok', detail=CAST(:d AS jsonb),
                  finished_at=now() WHERE id=:id""",
        id=run_id, d=__import__("json").dumps(summary),
    )
    return summary


@router.get("/sites/{site_id}/segments")
def get_segments(site_id: int) -> dict:
    """Current segment mix, with the cold-start share made explicit."""
    _require_site(site_id)

    rows = db.fetch_all(
        """
        SELECT segment_name,
               COUNT(*)                              AS visitors,
               COUNT(*) FILTER (WHERE is_cold_start) AS cold_start,
               ROUND(AVG(segment_confidence), 3)::float8 AS avg_confidence
        FROM user_segments
        WHERE site_id = :site_id
        GROUP BY segment_name
        ORDER BY visitors DESC
        """,
        site_id=site_id,
    )

    last = db.fetch_one(
        """
        SELECT detail, finished_at FROM pipeline_runs
        WHERE site_id = :site_id AND stage = 'segmentation' AND status = 'ok'
        ORDER BY finished_at DESC LIMIT 1
        """,
        site_id=site_id,
    )

    total = sum(r["visitors"] for r in rows)
    return {
        "segments": rows,
        "total": total,
        "cold_start_total": sum(r["cold_start"] for r in rows),
        "last_run": last["detail"] if last else None,
        "last_run_at": last["finished_at"] if last else None,
    }
