"""Event ingestion — the endpoint the mos.js snippet posts to.

This is where the marketing audience actually comes from: real visitors on the
client's website, not an uploaded spreadsheet. Every row in `visitors` and
`events` originates here.

Two things matter for correctness and for the viva:

1. **The snippet is public.** `site_key` travels in the page source, so this
   endpoint authenticates the *site*, never the *user*. It can therefore only
   ever append events for that site — it can read nothing back.
2. **Consent is explicit.** An `identify` event attaches an email to a visitor,
   but `email_consent` is only ever set true when the visitor ticked the box.
   Nothing else in the system may email a visitor without it.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from api import db

log = logging.getLogger("mos.collect")

router = APIRouter(tags=["tracking"])

MAX_EVENTS_PER_BATCH = 50
MAX_PROP_CHARS = 2_000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")

# Event types the tracker emits automatically. Custom types from mos.track()
# are also accepted — they are just stored — but these are the ones the
# feature builder in Module 1 understands.
KNOWN_EVENTS = {
    "page_view", "click", "scroll", "form_submit", "page_exit",
    "identify", "consent", "add_to_cart", "purchase", "signup", "demo_request",
}


def _clean(value: Any, limit: int = 300) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:limit] or None


def _parse_body(raw: bytes) -> dict:
    """The tracker sends text/plain to avoid a CORS preflight, so we parse the
    body ourselves rather than relying on FastAPI's JSON handling."""
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(400, f"Malformed payload: {exc}") from exc
    if not isinstance(payload, dict):
        raise HTTPException(400, "Payload must be a JSON object")
    return payload


def _resolve_site(site_key: str) -> dict:
    site = db.fetch_one("SELECT id FROM sites WHERE site_key = :k", k=site_key)
    if site is None:
        raise HTTPException(404, "Unknown site_key")
    return site


def _upsert_visitor(site_id: int, visitor_uid: str, ctx: dict) -> int:
    """Create the visitor on first sight; afterwards only refresh last_seen.

    Acquisition attributes (utm_*, referrer) are deliberately written once, on
    first sight, so a returning visitor is still credited to the campaign that
    originally brought them in — which is what attribution in Module 3 needs.
    """
    row = db.fetch_one(
        """
        INSERT INTO visitors (site_id, visitor_uid, utm_source, utm_medium,
                              utm_campaign, referrer, device)
        VALUES (:site_id, :uid, :utm_source, :utm_medium,
                :utm_campaign, :referrer, :device)
        ON CONFLICT (site_id, visitor_uid) DO UPDATE
            SET last_seen = now(),
                device    = COALESCE(visitors.device, EXCLUDED.device)
        RETURNING id
        """,
        site_id=site_id,
        uid=visitor_uid,
        utm_source=_clean(ctx.get("utm_source"), 120),
        utm_medium=_clean(ctx.get("utm_medium"), 120),
        utm_campaign=_clean(ctx.get("utm_campaign"), 120),
        referrer=_clean(ctx.get("referrer"), 500),
        device=_clean(ctx.get("device"), 20),
    )
    assert row is not None
    return int(row["id"])


def _apply_identify(visitor_id: int, props: dict) -> None:
    """Attach an email to a visitor, and grant consent only if explicitly given."""
    email = _clean(props.get("email"), 320)
    if not email or not EMAIL_RE.match(email):
        log.info("identify ignored — invalid email for visitor %s", visitor_id)
        return

    consent = props.get("consent") is True

    db.execute(
        """
        UPDATE visitors
           SET email      = :email,
               name       = COALESCE(:name, name),
               -- consent can only ever be turned ON here, never silently off
               email_consent = visitors.email_consent OR :consent,
               consent_at = CASE
                   WHEN :consent AND visitors.consent_at IS NULL THEN now()
                   ELSE visitors.consent_at END,
               last_seen  = now()
         WHERE id = :vid
        """,
        vid=visitor_id,
        email=email.lower(),
        name=_clean(props.get("name"), 120),
        consent=consent,
    )


#: How long after a click a purchase is still credited to that campaign.
ATTRIBUTION_WINDOW_DAYS = 7


def _attribute_conversion(site_id: int, visitor_id: int, props: dict) -> None:
    """Close the loop: credit an on-site purchase back to the message that
    earned the click.

    This is what turns email tracking into a funnel. Without it we would know
    that someone clicked and, separately, that someone bought, but never that
    the campaign caused the purchase.

    Last-touch within a fixed window, deliberately: it is the simplest rule that
    can be stated plainly and audited. Module 3 then compares first-touch,
    last-touch and multi-touch attribution over these same interactions, so the
    choice made here does not constrain the analysis.
    """
    click = db.fetch_one(
        f"""
        SELECT id, campaign_id, send_id, strategy, channel
        FROM interactions
        WHERE visitor_id = :vid
          AND event_type = 'click'
          AND occurred_at > now() - interval '{ATTRIBUTION_WINDOW_DAYS} days'
        ORDER BY occurred_at DESC
        LIMIT 1
        """,
        vid=visitor_id,
    )
    if click is None:
        return    # organic conversion — real, but not ours to claim

    already = db.fetch_one(
        """SELECT 1 AS ok FROM interactions
           WHERE send_id = :sid AND event_type = 'convert' LIMIT 1""",
        sid=click["send_id"],
    )
    if already:
        return

    db.execute(
        """
        INSERT INTO interactions (site_id, visitor_id, campaign_id, send_id,
                                  strategy, channel, platform, event_type,
                                  source, meta)
        VALUES (:site_id, :vid, :cid, :sid, :strategy, :channel, 'email',
                'convert',
                (SELECT source FROM visitors WHERE id = :vid),
                CAST(:meta AS jsonb))
        """,
        site_id=site_id, vid=visitor_id, cid=click["campaign_id"],
        sid=click["send_id"], strategy=click["strategy"],
        channel=click["channel"],
        meta=json.dumps({
            "attribution": "last_touch",
            "window_days": ATTRIBUTION_WINDOW_DAYS,
            "value": props.get("value"),
            "plan": props.get("plan"),
        }),
    )
    log.info("attributed conversion for visitor %s to send %s",
             visitor_id, click["send_id"])


def _apply_consent(visitor_id: int, props: dict) -> None:
    """Explicit consent toggle. Withdrawal is honoured immediately."""
    granted = props.get("consent") is True
    db.execute(
        """
        UPDATE visitors
           SET email_consent   = :granted,
               consent_at      = CASE WHEN :granted THEN now() ELSE consent_at END,
               unsubscribed_at = CASE WHEN :granted THEN NULL ELSE now() END
         WHERE id = :vid
        """,
        vid=visitor_id,
        granted=granted,
    )


@router.post("/collect")
async def collect(request: Request) -> Response:
    """Accept a batch of tracked events from mos.js."""
    payload = _parse_body(await request.body())

    site_key = _clean(payload.get("site_key"), 100)
    visitor_uid = _clean(payload.get("visitor_uid"), 100)
    if not site_key or not visitor_uid:
        raise HTTPException(400, "site_key and visitor_uid are required")

    events = payload.get("events") or []
    if not isinstance(events, list):
        raise HTTPException(400, "events must be a list")
    if len(events) > MAX_EVENTS_PER_BATCH:
        raise HTTPException(413, f"Batch too large (max {MAX_EVENTS_PER_BATCH})")

    ctx = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    site_id = _resolve_site(site_key)["id"]
    visitor_id = _upsert_visitor(site_id, visitor_uid, ctx)
    session_id = _clean(payload.get("session_id"), 100)

    rows: list[dict] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        event_type = _clean(ev.get("type"), 60)
        if not event_type:
            continue

        props = ev.get("props") if isinstance(ev.get("props"), dict) else {}
        props_json = json.dumps(props)[:MAX_PROP_CHARS]

        # Side effects beyond simply storing the event.
        if event_type == "identify":
            _apply_identify(visitor_id, props)
        elif event_type == "consent":
            _apply_consent(visitor_id, props)
        elif event_type in ("purchase", "convert"):
            _attribute_conversion(site_id, visitor_id, props)

        rows.append({
            "site_id": site_id,
            "visitor_id": visitor_id,
            "session_id": session_id,
            "event_type": event_type,
            "path": _clean(ev.get("path") or ctx.get("path"), 500),
            "referrer": _clean(ctx.get("referrer"), 500),
            "props": props_json,
            "occurred_at": _parse_ts(ev.get("ts")),
        })

    if rows:
        db.execute_many(
            """
            INSERT INTO events (site_id, visitor_id, session_id, event_type,
                                path, referrer, props, occurred_at)
            VALUES (:site_id, :visitor_id, :session_id, :event_type,
                    :path, :referrer, CAST(:props AS jsonb), :occurred_at)
            """,
            rows,
        )

    # The tracker never reads a response body; 204 keeps the payload at zero.
    return Response(status_code=204)


def _parse_ts(value: Any) -> datetime:
    """Trust but verify the client clock: fall back to server time if unusable."""
    if isinstance(value, str):
        try:
            ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts
        except ValueError:
            pass
    return datetime.now(timezone.utc)


@router.options("/collect")
async def collect_preflight() -> Response:
    """Some browsers still preflight; answer permissively for this one route."""
    return Response(status_code=204)
