"""Campaign endpoints — create, send, advance, and measure."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from api import db
from api.services import campaigns as svc
from api.services import email_sender
from api.services import research_m2
from api.settings import get_settings

router = APIRouter(tags=["campaigns"])


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    strategy: str = Field("hybrid", pattern="^(fixed|trigger|hybrid)$")
    segments: list[str] | None = Field(
        None, description="Restrict to these segment names; omit for the whole audience")
    limit: int | None = Field(
        None, ge=1, le=10_000, description="Cap the number of recipients")


def _require_site(site_id: int) -> None:
    if db.fetch_one("SELECT 1 AS ok FROM sites WHERE id = :i", i=site_id) is None:
        raise HTTPException(404, "Site not found")


@router.get("/sites/{site_id}/audience/reachable")
def reachable_audience(site_id: int) -> dict:
    """Who may lawfully be emailed, and why the rest may not.

    Exposed on its own because the gap between "visitors" and "contactable" is
    the single most misread number in a marketing dashboard.
    """
    _require_site(site_id)

    counts = db.fetch_one(
        """
        SELECT count(*)                                             AS visitors,
               count(*) FILTER (WHERE email IS NULL)                AS anonymous,
               count(*) FILTER (WHERE email IS NOT NULL
                                 AND NOT email_consent
                                 AND unsubscribed_at IS NULL)       AS known_no_consent,
               count(*) FILTER (WHERE unsubscribed_at IS NOT NULL)  AS unsubscribed,
               count(*) FILTER (WHERE email IS NOT NULL
                                 AND email_consent
                                 AND unsubscribed_at IS NULL)       AS reachable
        FROM visitors WHERE site_id = :s
        """,
        s=site_id,
    )

    by_segment = db.fetch_all(
        """
        SELECT COALESCE(sg.segment_name, 'unsegmented') AS segment_name,
               count(*) AS reachable
        FROM visitors v
        LEFT JOIN user_segments sg ON sg.visitor_id = v.id
        WHERE v.site_id = :s AND v.email IS NOT NULL
          AND v.email_consent AND v.unsubscribed_at IS NULL
        GROUP BY 1 ORDER BY reachable DESC
        """,
        s=site_id,
    )

    return {
        **(counts or {}),
        "reachable_by_segment": by_segment,
        "explanation": (
            "Only visitors who explicitly ticked the consent box can be emailed. "
            "Anonymous visitors have never given an address; known-no-consent "
            "gave one without opting in."
        ),
    }


@router.post("/sites/{site_id}/campaigns", status_code=201)
def create_campaign(site_id: int, payload: CampaignCreate) -> dict:
    """Create a campaign and schedule its first messages."""
    _require_site(site_id)
    try:
        return svc.create_campaign(
            site_id, payload.name, payload.strategy, payload.segments, payload.limit)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/sites/{site_id}/campaigns")
def list_campaigns(site_id: int) -> dict:
    """Every campaign for this site, with its live metrics side by side."""
    _require_site(site_id)
    return {
        "campaigns": svc.compare_strategies(site_id),
        "email_delivery": "live" if get_settings().email_enabled else "dry_run",
    }


@router.get("/research/m2/results")
def module2_research_results() -> dict:
    """Module 2's actual controlled-simulation research output, read from
    the committed pipeline result files. Distinct from the live
    operational campaign view."""
    return research_m2.get_results()


@router.get("/research/m2/figures/{name}")
def module2_figure(name: str) -> FileResponse:
    """Serve one of Module 2's 6 result figures by exact filename.

    Validated against a fixed allowlist — same reasoning as the mos.js route
    in api/main.py, but for these six files specifically, so this can never
    become an arbitrary path read."""
    path = research_m2.figure_path(name)
    if path is None:
        raise HTTPException(404, "Figure not found")
    return FileResponse(
        path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/campaigns/{campaign_id}")
def get_campaign(campaign_id: int) -> dict:
    try:
        metrics = svc.campaign_metrics(campaign_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

    sends = db.fetch_all(
        """
        SELECT s.id, s.step, s.subject, s.status, s.scheduled_for, s.sent_at,
               v.email, sg.segment_name,
               count(i.id) FILTER (WHERE i.event_type='open')  AS opens,
               count(i.id) FILTER (WHERE i.event_type='click') AS clicks
        FROM campaign_sends s
        JOIN visitors v ON v.id = s.visitor_id
        LEFT JOIN user_segments sg ON sg.visitor_id = v.id
        LEFT JOIN interactions  i  ON i.send_id = s.id
        WHERE s.campaign_id = :cid
        GROUP BY s.id, v.email, sg.segment_name
        ORDER BY s.scheduled_for DESC, s.id DESC
        LIMIT 200
        """,
        cid=campaign_id,
    )
    return {"metrics": metrics, "sends": sends}


@router.post("/campaigns/{campaign_id}/send")
def send_campaign(campaign_id: int, limit: int = 200, force: bool = False) -> dict:
    """Deliver messages that are due.

    `force=true` ignores the schedule so a multi-day sequence can be shown in a
    single demo. With SMTP unconfigured this is a dry run: messages are composed
    and recorded, but nothing leaves the machine.
    """
    if db.fetch_one("SELECT 1 AS ok FROM campaigns WHERE id=:i", i=campaign_id) is None:
        raise HTTPException(404, "Campaign not found")

    result = email_sender.deliver_due_sends(campaign_id, limit=limit, force=force)
    db.execute(
        "UPDATE campaigns SET status='running', started_at=COALESCE(started_at, now()) "
        "WHERE id=:i", i=campaign_id)

    return {**result, "campaign_id": campaign_id,
            "metrics": svc.campaign_metrics(campaign_id)}


@router.post("/campaigns/{campaign_id}/advance")
def advance_campaign(campaign_id: int, silence_days: int = 2) -> dict:
    """Queue the next message for each recipient based on observed behaviour."""
    try:
        return svc.advance_triggers(campaign_id, silence_days=silence_days)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/campaigns/scheduler/run")
def run_scheduler(
    x_scheduler_token: str | None = Header(default=None),
) -> dict:
    """One tick of the plan clock — what a cron job calls in production.

    This platform advises rather than delivers, so the tick's job is to keep
    the Action Plan current: for every running plan it re-reads what recipients
    actually did and queues the next recommended message. New actions then
    appear on the dashboard for the company to send from its own tools.

    Delivery is deliberately NOT part of the tick. A background job that mails
    people on a schedule is exactly the behaviour that turns an advisory system
    into an unattended bulk sender. Companies that have opted into SMTP send
    explicitly via POST /campaigns/{id}/send.

    When SCHEDULER_TOKEN is set (any real deployment), the caller must send it
    in the X-Scheduler-Token header; locally, with no token configured, the
    endpoint stays open.
    """
    settings = get_settings()
    if settings.scheduler_token and x_scheduler_token != settings.scheduler_token:
        raise HTTPException(401, "Invalid scheduler token")

    running = db.fetch_all(
        "SELECT id FROM campaigns WHERE status = 'running' ORDER BY id")

    ticked = []
    for row in running:
        cid = row["id"]
        try:
            advanced = svc.advance_triggers(cid)
            ticked.append({"campaign_id": cid,
                           "new_actions": advanced.get("queued", 0)})
        except Exception as exc:  # one broken plan must not stall the rest
            ticked.append({"campaign_id": cid, "error": str(exc)})

    return {
        "plans_ticked": len(ticked),
        "results": ticked,
        "note": ("New actions were added to the Action Plan. Nothing was sent — "
                 "this platform recommends, the company executes."),
    }
