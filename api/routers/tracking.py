"""Email tracking — the endpoints that turn a sent message into observed data.

Three public routes, all reachable from a recipient's email client:

    GET /track/open/{token}.gif     invisible pixel  → records an `open`
    GET /track/click/{token}/{i}    tracked link     → records a `click`, redirects
    GET /unsubscribe/{token}        one-click opt-out → revokes consent

Every hit writes a row to `interactions`, carrying the provenance of the
visitor it belongs to, which is what lets the Module 3 funnel say whether it
measured a live browser or replayed the research dataset.

Two design points worth defending in a viva:

*   **Redirect targets are resolved server-side by index.** The URL carries
    `/track/click/{token}/2`, not `?url=https://…`, so the endpoint can only
    ever send someone to a link that was in the message we composed. A
    query-string redirector would be an open redirect — a real phishing vector.

*   **Open tracking is best-effort and known to under-report.** Most mail
    clients block remote images by default, so a missing `open` does not mean
    the message was not read. Clicks are the reliable signal. The analytics
    module is told this so the funnel is not over-interpreted.
"""

from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from api import db

log = logging.getLogger("mos.tracking")

router = APIRouter(tags=["tracking"])

# A 1×1 fully transparent GIF.
PIXEL = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)

NO_STORE = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
}


def _load_send(token: str) -> dict | None:
    return db.fetch_one(
        """
        SELECT s.id, s.campaign_id, s.visitor_id, s.channel, s.links,
               c.site_id, c.strategy
        FROM campaign_sends s
        JOIN campaigns c ON c.id = s.campaign_id
        WHERE s.track_token = :t
        """,
        t=token,
    )


def _record(send: dict, event_type: str, request: Request, **meta) -> None:
    """Append one funnel event. Opens are deduplicated; clicks are not.

    A mail client may fetch the pixel repeatedly (previews, re-opens), and
    counting those as separate opens would inflate the open rate. Repeat clicks
    are genuine re-engagement, so they are all kept.
    """
    if event_type == "open":
        existing = db.fetch_one(
            """SELECT 1 AS ok FROM interactions
               WHERE send_id = :sid AND event_type = 'open' LIMIT 1""",
            sid=send["id"],
        )
        if existing:
            return

    import json

    db.execute(
        """
        INSERT INTO interactions (site_id, visitor_id, campaign_id, send_id,
                                  strategy, channel, platform, event_type,
                                  source, meta)
        VALUES (:site_id, :visitor_id, :campaign_id, :send_id,
                :strategy, :channel, :platform, :event_type,
                -- Derived, never asserted: an event inherits the provenance of
                -- the visitor it belongs to, even though it arrived through
                -- this same real endpoint.
                (SELECT source FROM visitors WHERE id = :visitor_id),
                CAST(:meta AS jsonb))
        """,
        site_id=send["site_id"],
        visitor_id=send["visitor_id"],
        campaign_id=send["campaign_id"],
        send_id=send["id"],
        strategy=send.get("strategy"),
        channel=send.get("channel", "email"),
        platform="email",
        event_type=event_type,
        meta=json.dumps({
            "user_agent": request.headers.get("user-agent", "")[:300],
            **meta,
        }),
    )


@router.get("/track/open/{token}.gif", include_in_schema=False)
def track_open(token: str, request: Request) -> Response:
    """Invisible pixel. Always returns an image, even for an unknown token —
    a broken image in someone's inbox would be a poor way to signal an error."""
    send = _load_send(token)
    if send:
        try:
            _record(send, "open", request)
        except Exception:            # never let tracking break the render
            log.exception("failed to record open for %s", token)
    return Response(content=PIXEL, media_type="image/gif", headers=NO_STORE)


@router.get("/track/click/{token}/{index}", include_in_schema=False)
def track_click(token: str, index: int, request: Request) -> Response:
    """Record a click, then forward to the link stored for this message."""
    send = _load_send(token)
    if not send:
        return HTMLResponse("<h1>Link expired</h1>", status_code=404)

    links = send.get("links") or []
    if not isinstance(links, list) or index < 0 or index >= len(links):
        return HTMLResponse("<h1>Link not found</h1>", status_code=404)

    target = str(links[index])
    try:
        _record(send, "click", request, link_index=index, url=target)
    except Exception:
        log.exception("failed to record click for %s", token)

    # 302: this destination is per-message and must never be cached by a proxy.
    return RedirectResponse(url=target, status_code=302, headers=NO_STORE)


@router.get("/unsubscribe/{token}", include_in_schema=False)
def unsubscribe(token: str, request: Request) -> HTMLResponse:
    """One-click opt-out. No login, no confirmation step, no dark patterns."""
    send = _load_send(token)
    if not send:
        return HTMLResponse("<h1>Link expired</h1>", status_code=404)

    db.execute(
        """
        UPDATE visitors
           SET email_consent = FALSE, unsubscribed_at = now()
         WHERE id = :vid
        """,
        vid=send["visitor_id"],
    )
    try:
        _record(send, "unsubscribe", request)
    except Exception:
        log.exception("failed to record unsubscribe for %s", token)

    # Anything still queued for this person is cancelled immediately.
    db.execute(
        """
        UPDATE campaign_sends SET status = 'skipped',
               error = 'recipient unsubscribed'
         WHERE visitor_id = :vid AND status = 'scheduled'
        """,
        vid=send["visitor_id"],
    )

    return HTMLResponse(
        """
        <!doctype html><meta charset="utf-8">
        <title>Unsubscribed</title>
        <style>
          body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
               display:grid;place-items:center;height:100vh;margin:0;color:#0f172a;
               background:#f8fafc}
          .card{background:#fff;padding:40px 48px;border-radius:16px;text-align:center;
                box-shadow:0 8px 30px rgb(15 23 42/.08);max-width:420px}
          h1{margin:0 0 8px;font-size:1.4rem} p{color:#64748b;margin:0;line-height:1.6}
        </style>
        <div class="card">
          <h1>You have been unsubscribed</h1>
          <p>You will not receive further marketing email from us.
             Any messages already queued have been cancelled.</p>
        </div>
        """,
        headers=NO_STORE,
    )


@router.get("/l/{token}", include_in_schema=False)
def short_link(token: str) -> Response:
    """The link a company pastes into a post it publishes itself.

    This is what keeps an advisory system measurable. The platform never
    published the post, but the link inside it is ours: the click is counted
    here, and the visitor is forwarded to the company's site with UTM
    parameters attached, so `mos.js` records which platform sent them. The
    attribution model already treats that UTM as the acquisition touch, so a
    hand-published Instagram post lands in the same funnel as everything else.

    Unknown tokens still redirect somewhere sensible rather than showing an
    error — a marketing link that 404s in public is worse than an untracked one.
    """
    row = db.fetch_one(
        """
        SELECT a.id, a.target_url, a.platform, s.url AS site_url
        FROM content_actions a
        JOIN sites s ON s.id = a.site_id
        WHERE a.track_token = :t
        """,
        t=token,
    )
    if row is None:
        log.info("short link %s not recognised", token[:8])
        return RedirectResponse("/", status_code=302, headers=NO_STORE)

    # Clicks accumulate on the action itself. There is no visitor to attach
    # them to yet — the person is anonymous until they land on the site and
    # mos.js identifies them, which is exactly what the redirect sets up.
    db.execute(
        """
        UPDATE content_actions
        SET outcome = jsonb_set(
                COALESCE(outcome, '{}'::jsonb), '{clicks}',
                to_jsonb(COALESCE((outcome->>'clicks')::int, 0) + 1))
        WHERE id = :i
        """,
        i=row["id"],
    )
    return RedirectResponse(row["target_url"] or row["site_url"],
                            status_code=302, headers=NO_STORE)
