"""Content endpoints — read the client's website, generate platform assets."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api import db
from api.services import content as svc

router = APIRouter(tags=["content"])


class GenerateRequest(BaseModel):
    platforms: list[str] | None = Field(
        None, description=f"Subset of {svc.SUPPORTED_PLATFORMS}; omit for all")
    engine: str = Field("fast", pattern="^(fast|phi3)$")
    use_website: bool = Field(
        True, description="Read the product's own site before writing")
    campaign_id: int | None = None


def _require_site(site_id: int) -> None:
    if db.fetch_one("SELECT 1 AS ok FROM sites WHERE id = :i", i=site_id) is None:
        raise HTTPException(404, "Site not found")


@router.post("/sites/{site_id}/crawl")
def crawl(site_id: int, force: bool = Query(False, description="Ignore the cache")) -> dict:
    """Fetch the site's marketing copy and show what was extracted."""
    _require_site(site_id)
    try:
        return svc.crawl_site(site_id, force=force)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/sites/{site_id}/content/generate")
def generate(site_id: int, payload: GenerateRequest) -> dict:
    """Generate, score and store platform-native content for this site.

    Platform order comes from Module 3's attribution, so channels that actually
    earn conversions are written for first.
    """
    _require_site(site_id)

    if payload.platforms:
        unknown = set(payload.platforms) - set(svc.SUPPORTED_PLATFORMS)
        if unknown:
            raise HTTPException(400, f"Unsupported platforms: {sorted(unknown)}")

    try:
        return svc.generate_for_site(
            site_id, platforms=payload.platforms, engine=payload.engine,
            campaign_id=payload.campaign_id, use_website=payload.use_website)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        db.execute(
            """INSERT INTO pipeline_runs (site_id, stage, status, error, finished_at)
               VALUES (:s, 'content', 'failed', :e, now())""",
            s=site_id, e=str(exc)[:2000])
        raise HTTPException(500, f"Content generation failed: {exc}") from exc


@router.get("/sites/{site_id}/content")
def list_content(site_id: int, platform: str | None = None,
                 limit: int = Query(50, ge=1, le=200)) -> dict:
    """Stored assets, newest and highest-scoring first."""
    _require_site(site_id)
    return svc.list_assets(site_id, platform=platform, limit=limit)


@router.get("/sites/{site_id}/content/priorities")
def priorities(site_id: int) -> dict:
    """Which platforms analytics says to prioritise, and on what evidence."""
    _require_site(site_id)
    return svc.platform_priorities(site_id)
