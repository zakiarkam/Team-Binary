"""Email delivery — composing, tracking and sending campaign messages.

Safety is enforced here rather than left to the caller, because the cost of
getting it wrong is mailing a real person who never asked to hear from us:

  1. `eligible_recipients()` is the only way to select an audience, and it
     filters on `email_consent` and `unsubscribed_at` in SQL.
  2. Dry-run is the default. With `SMTP_HOST` unset, messages are composed,
     tracked and recorded exactly as normal but never handed to a mail server,
     so the whole pipeline can be demonstrated with zero delivery risk.
  3. Every message carries a working one-click unsubscribe link. No exceptions —
     `compose()` builds it into both the HTML and plain-text parts.
"""

from __future__ import annotations

import html
import logging
import re
import secrets
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Any

from api import db
from api.settings import get_settings

log = logging.getLogger("mos.email")

# Turns [label](https://url) in body copy into a tracked link.
LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")


def new_track_token() -> str:
    return secrets.token_urlsafe(24)


# ── Audience selection ───────────────────────────────────────────────────────
def eligible_recipients(site_id: int, segments: list[str] | None = None,
                        limit: int | None = None) -> list[dict]:
    """Visitors this system is permitted to email.

    The consent conditions live in the query rather than in Python so that no
    caller can accidentally skip them.
    """
    filters = [
        "v.site_id = :site_id",
        "v.email IS NOT NULL",
        "v.email_consent = TRUE",         # explicit opt-in
        "v.unsubscribed_at IS NULL",      # never re-mail an unsubscriber
    ]
    if segments:
        filters.append("s.segment_name = ANY(:segments)")

    sql = f"""
        SELECT v.id AS visitor_id, v.email, v.name, v.is_synthetic,
               s.segment_name, s.segment_confidence, s.is_cold_start,
               a.predicted_conversion, a.drop_off_risk
        FROM visitors v
        LEFT JOIN user_segments    s ON s.visitor_id = v.id
        LEFT JOIN analytics_output a ON a.visitor_id = v.id
        WHERE {' AND '.join(filters)}
        ORDER BY COALESCE(a.predicted_conversion, 0) DESC, v.last_seen DESC
        {'LIMIT :limit' if limit else ''}
    """
    return db.fetch_all(sql, site_id=site_id, segments=segments, limit=limit)


# ── Composition ──────────────────────────────────────────────────────────────
def compose(subject: str, body_markdown: str, token: str,
            recipient_name: str | None = None) -> dict[str, Any]:
    """Render one message, rewriting links for tracking.

    Returns the HTML part, the plain-text part, and the ordered list of link
    targets. The list is stored on the send row so `/track/click/{token}/{i}`
    can resolve a destination without ever trusting a URL from the request.
    """
    settings = get_settings()
    base = settings.public_api_url.rstrip("/")

    greeting = f"Hi {recipient_name.split()[0]}," if recipient_name else "Hi,"
    links: list[str] = []

    def _track(match: re.Match) -> str:
        label, url = match.group(1), match.group(2)
        links.append(url)
        return f'<a href="{base}/track/click/{token}/{len(links) - 1}">{html.escape(label)}</a>'

    html_body = LINK_RE.sub(_track, html.escape(body_markdown, quote=False))
    # Restore the anchors the escaping above would otherwise have mangled.
    html_body = html_body.replace("&lt;a href", "<a href").replace("&lt;/a&gt;", "</a>")
    html_body = html_body.replace("\n\n", "</p><p>").replace("\n", "<br>")

    text_body = LINK_RE.sub(lambda m: f"{m.group(1)}: {m.group(2)}", body_markdown)

    unsubscribe_url = f"{base}/unsubscribe/{token}"
    pixel_url = f"{base}/track/open/{token}.gif"

    html_doc = f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#f6f8fb;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background:#f6f8fb;padding:28px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
             style="max-width:560px;background:#ffffff;border-radius:14px;
                    padding:32px 34px;font-family:-apple-system,BlinkMacSystemFont,
                    'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#0f172a;
                    line-height:1.6;">
        <tr><td>
          <p style="margin:0 0 14px;">{html.escape(greeting)}</p>
          <p style="margin:0 0 18px;">{html_body}</p>
          <hr style="border:0;border-top:1px solid #e2e8f0;margin:26px 0 14px;">
          <p style="margin:0;font-size:12px;color:#94a3b8;">
            You are receiving this because you opted in on our website.
            <a href="{unsubscribe_url}" style="color:#94a3b8;">Unsubscribe</a>.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
  <img src="{pixel_url}" width="1" height="1" alt="" style="display:block;border:0;">
</body></html>"""

    text_doc = (
        f"{greeting}\n\n{text_body}\n\n"
        f"---\nYou are receiving this because you opted in on our website.\n"
        f"Unsubscribe: {unsubscribe_url}\n"
    )

    return {"html": html_doc, "text": text_doc, "links": links,
            "unsubscribe_url": unsubscribe_url}


# ── Delivery ─────────────────────────────────────────────────────────────────
class DeliveryResult(dict):
    """`{sent, failed, dry_run, errors}` — a dict so it serialises directly."""


def _smtp_send(to_email: str, to_name: str | None, subject: str,
               html_body: str, text_body: str, unsubscribe_url: str) -> str:
    """Hand one message to the configured SMTP server. Returns its Message-ID."""
    settings = get_settings()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_email))
    msg["To"] = formataddr((to_name or "", to_email))
    message_id = make_msgid()
    msg["Message-ID"] = message_id

    # RFC 8058: lets Gmail/Outlook show a native unsubscribe button, which keeps
    # complaints (and therefore the sending reputation) low.
    msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)

    return message_id


def deliver_due_sends(campaign_id: int, limit: int = 200,
                      force: bool = False) -> DeliveryResult:
    """Send every scheduled message whose time has come.

    `force` ignores `scheduled_for`, which is what the demo uses so a campaign
    can be shown start-to-finish without waiting days for the sequence.
    """
    settings = get_settings()
    dry_run = not settings.email_enabled

    due = db.fetch_all(
        f"""
        SELECT s.id, s.subject, s.body_html, s.body_text, s.track_token,
               v.email, v.name, v.email_consent, v.unsubscribed_at
        FROM campaign_sends s
        JOIN visitors v ON v.id = s.visitor_id
        WHERE s.campaign_id = :cid
          AND s.status = 'scheduled'
          {'' if force else 'AND s.scheduled_for <= now()'}
        ORDER BY s.scheduled_for
        LIMIT :limit
        """,
        cid=campaign_id, limit=limit,
    )

    sent = failed = skipped = 0
    errors: list[str] = []

    for row in due:
        # Re-check consent at the moment of sending: someone may have
        # unsubscribed between scheduling and delivery.
        if not row["email_consent"] or row["unsubscribed_at"] is not None:
            db.execute(
                """UPDATE campaign_sends SET status='skipped',
                          error='no consent at send time' WHERE id=:id""",
                id=row["id"])
            skipped += 1
            continue

        try:
            if dry_run:
                message_id = f"dry-run-{row['track_token'][:12]}"
                status = "dry_run"
            else:
                unsub = f"{settings.public_api_url.rstrip('/')}/unsubscribe/{row['track_token']}"
                message_id = _smtp_send(
                    row["email"], row["name"], row["subject"],
                    row["body_html"], row["body_text"], unsub)
                status = "sent"

            db.execute(
                """UPDATE campaign_sends
                      SET status=:status, sent_at=now(), provider_message_id=:mid
                    WHERE id=:id""",
                id=row["id"], status=status, mid=message_id)

            # A `sent` interaction is recorded in both modes: the funnel's top
            # stage is "we dispatched a message", and in dry-run we genuinely
            # did everything except hand it to a mail server.
            db.execute(
                """
                INSERT INTO interactions (site_id, visitor_id, campaign_id, send_id,
                                          strategy, channel, platform, event_type,
                                          is_real, meta)
                SELECT c.site_id, s.visitor_id, s.campaign_id, s.id,
                       c.strategy, s.channel, 'email', 'sent',
                       -- Simulated recipients produce simulated funnel rows.
                       NOT v.is_synthetic,
                       CAST(:meta AS jsonb)
                FROM campaign_sends s
                JOIN campaigns c ON c.id = s.campaign_id
                JOIN visitors  v ON v.id = s.visitor_id
                WHERE s.id = :id
                """,
                id=row["id"],
                meta=f'{{"dry_run": {str(dry_run).lower()}}}',
            )
            sent += 1

        except Exception as exc:
            failed += 1
            errors.append(f"{row['email']}: {type(exc).__name__}: {exc}")
            db.execute(
                "UPDATE campaign_sends SET status='failed', error=:e WHERE id=:id",
                id=row["id"], e=str(exc)[:2000])
            log.exception("send %s failed", row["id"])

    log.info("campaign %s: sent=%s skipped=%s failed=%s dry_run=%s",
             campaign_id, sent, skipped, failed, dry_run)

    return DeliveryResult(
        sent=sent, skipped=skipped, failed=failed,
        dry_run=dry_run, errors=errors[:10],
    )
