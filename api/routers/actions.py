"""Action Plan endpoints — the platform's primary output.

The company asks "what should I do next?" and gets back a prioritised list of
actions with the content already written. It executes them in its own tools
and marks them done.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api import db
from api.services import actions as svc

router = APIRouter(tags=["actions"])


class PlanRequest(BaseModel):
    strategy: str = Field("hybrid", pattern="^(fixed|trigger|hybrid)$")
    segments: list[str] | None = None
    limit: int | None = Field(None, ge=1, le=10_000)


class ExecutedRequest(BaseModel):
    executed: bool = True
    notes: str | None = Field(None, max_length=2000)


def _require_site(site_id: int) -> None:
    if db.fetch_one("SELECT 1 AS ok FROM sites WHERE id = :i", i=site_id) is None:
        raise HTTPException(404, "Site not found")


@router.post("/sites/{site_id}/plan", status_code=201)
def create_plan(site_id: int, payload: PlanRequest) -> dict:
    """Work out what this company should do next and write the content."""
    _require_site(site_id)
    try:
        return svc.build_plan(site_id, payload.strategy,
                              payload.segments, payload.limit)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/sites/{site_id}/plan")
def get_plan(site_id: int, include_done: bool = False) -> dict:
    """The outstanding actions, each with copy-paste-ready content."""
    _require_site(site_id)
    return svc.current_plan(site_id, include_done=include_done)


@router.post("/actions/posts/{action_id}/executed")
def post_executed(action_id: int, payload: ExecutedRequest) -> dict:
    """The company published this post (or decided to skip it)."""
    try:
        return svc.mark_post_executed(action_id, payload.executed, payload.notes)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/actions/emails/{campaign_id}/{step}/executed")
def email_executed(campaign_id: int, step: int,
                   payload: ExecutedRequest) -> dict:
    """The company sent this message from their own email tool.

    Recorded as self-reported rather than observed — the platform did not
    watch it leave, so the funnel must not pretend otherwise.
    """
    if db.fetch_one("SELECT 1 AS ok FROM campaigns WHERE id = :i",
                    i=campaign_id) is None:
        raise HTTPException(404, "Plan not found")
    return svc.mark_email_executed(campaign_id, step, payload.executed)
