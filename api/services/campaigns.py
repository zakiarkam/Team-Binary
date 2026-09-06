"""Module 2 as a service — campaign automation over a real audience.

Implements the three automation policies the research compares, against live
opted-in visitors instead of a simulator:

    fixed    every recipient gets the same sequence on the same schedule
    trigger  only the first message is scheduled; what follows depends on what
             the recipient actually did (opened, clicked, or stayed silent)
    hybrid   a fixed backbone, adjusted by segment and predicted conversion

The research question — which policy gives the best engagement and conversion
for the least operational complexity — is now measurable on observed data,
because every send, open and click lands in `interactions` carrying the
provenance of the recipient it belongs to.

Operational complexity is recorded per campaign as the number of distinct
decision rules the policy needed, so the comparison is not purely about
outcomes: a policy that wins by a point but needs five times the rules is not
obviously better, and the report should be able to say so.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from api import db
from api.services import email_sender

log = logging.getLogger("mos.campaigns")

STRATEGIES = ("fixed", "trigger", "hybrid")

# ── Message sequence ─────────────────────────────────────────────────────────
# Mirrors Module 2's fixed workflow (welcome → product info → social proof →
# discount → final reminder). Phase 5 replaces these bodies with Module 4's
# generated, scored content; the scheduling logic does not change.
STEPS: list[dict[str, Any]] = [
    {
        "key": "welcome", "day": 0,
        "subject": "Welcome to {product}",
        "body": ("Thanks for joining the {product} list.\n\n"
                 "We make smart home devices that cut standby energy, secure the "
                 "place and take care of the small daily jobs — and every one of "
                 "them works on its own, so you can start with just the problem "
                 "that annoys you most.\n\n"
                 "[See the collection]({site_url})"),
    },
    {
        "key": "product_info", "day": 2,
        "subject": "Where most people start with {product}",
        "body": ("Most customers begin with the plugs or the motion light, see "
                 "the difference on the next bill, and add the hub later.\n\n"
                 "[Browse the devices]({site_url})"),
    },
    {
        "key": "social_proof", "day": 4,
        "subject": "What changed for homes like yours",
        "body": ("Customers using {product} report around 31% less standby "
                 "energy use, and most make the price of a plug pack back over "
                 "one winter.\n\n"
                 "[See what people bought]({site_url})"),
    },
    {
        "key": "discount", "day": 6,
        "subject": "A little help getting started",
        "body": ("If price is the blocker, the Pulse Door Sensor starts at $24 "
                 "and delivery is free over $75 — and you earn ten loyalty "
                 "points on every dollar either way.\n\n"
                 "[Check the prices]({site_url})"),
    },
    {
        "key": "final_reminder", "day": 8,
        "subject": "Last note from us",
        "body": ("We will stop emailing about this after today.\n\n"
                 "If it is useful, the whole collection is here:\n\n"
                 "[Shop {product}]({site_url})"),
    },
]

STEP_BY_KEY = {s["key"]: s for s in STEPS}

# Segment-specific overrides for the hybrid policy. This is the "segmentation
# intelligence" half of the hybrid strategy: the sequence is the same, but the
# opening message reflects what we already know about the recipient.
HYBRID_OPENERS = {
    "High Intent": {
        "subject": "Ready when you are, {product}",
        "body": ("You have been looking closely at {product} — happy to skip the "
                 "introduction.\n\n[Go straight to the collection]({site_url})"),
    },
    "Loyal Customer": {
        "subject": "Something new in store at {product}",
        "body": ("Thanks for shopping with us. Here is what landed recently — "
                 "and your loyalty points are waiting.\n\n"
                 "[See what's new]({site_url})"),
    },
    "Price Sensitive": {
        "subject": "{product} — what it costs",
        "body": ("Straight to the point: devices start at $24, delivery is free "
                 "over $75, and every dollar earns ten points.\n\n"
                 "[Compare the devices]({site_url})"),
    },
    "New Cold User": {
        "subject": "Getting started with {product}",
        "body": ("You are new here, so here is the short version of what "
                 "{product} makes and which device to buy first.\n\n"
                 "[The 2-minute version]({site_url})"),
    },
}

# How many distinct decision rules each policy needs. Used as the operational
# complexity metric in the strategy comparison.
POLICY_RULE_COUNT = {"fixed": 1, "trigger": 4, "hybrid": 4 + len(HYBRID_OPENERS)}


def _site(site_id: int) -> dict:
    row = db.fetch_one(
        "SELECT id, name, url, product_name FROM sites WHERE id = :i", i=site_id)
    if row is None:
        raise ValueError(f"Site {site_id} not found")
    return row


def _render(step: dict, site: dict, recipient: dict, token: str,
            generated: dict | None = None) -> dict:
    """Compose one message, preferring Module 4's generated copy when it exists.

    This is the content → campaign half of the closed loop. The hand-written
    templates below remain as the fallback so a campaign can still run before
    any content has been generated, but when Module 4 has produced a scored
    email asset for this site, that copy is what actually goes out.
    """
    product = site.get("product_name") or site["name"]
    fields = {"product": product, "site_url": site["url"].rstrip("/")}

    if generated and generated.get("caption"):
        from api.services.content import split_email_asset

        # The generated asset is a complete email; take its parts rather than
        # pasting it whole, or compose() adds a second subject and greeting.
        parsed_subject, body = split_email_asset(generated["caption"])
        subject = (generated.get("subject") or parsed_subject
                   or step["subject"].format(**fields))[:120]
        cta = (generated.get("cta") or "").strip()
        if cta:
            # Every message needs a tracked link, or there is no click to
            # measure. The generated caption usually already ends with the call
            # to action, so turn that sentence into the link instead of
            # repeating it underneath.
            link = f"[{cta}]({fields['site_url']})"
            if body.rstrip().endswith(cta):
                body = body.rstrip()[: -len(cta)].rstrip() + f"\n\n{link}"
            else:
                body = f"{body}\n\n{link}"
    else:
        subject = step["subject"].format(**fields)
        body = step["body"].format(**fields)

    composed = email_sender.compose(subject, body, token, recipient.get("name"))
    return {"subject": subject, **composed}


def _queue_send(campaign_id: int, recipient: dict, step: dict, site: dict,
                when: datetime, step_index: int,
                generated: dict | None = None) -> None:
    token = email_sender.new_track_token()
    rendered = _render(step, site, recipient, token, generated)

    db.execute(
        """
        INSERT INTO campaign_sends (campaign_id, visitor_id, content_asset_id,
                                    step, channel, subject, body_html, body_text,
                                    scheduled_for, status, track_token, links)
        VALUES (:cid, :vid, :asset, :step, 'email', :subject, :html, :text,
                :when, 'scheduled', :token, CAST(:links AS jsonb))
        """,
        cid=campaign_id, vid=recipient["visitor_id"],
        asset=(generated or {}).get("id"), step=step_index,
        subject=rendered["subject"], html=rendered["html"], text=rendered["text"],
        when=when, token=token, links=json.dumps(rendered["links"]),
    )


# ── Creation ─────────────────────────────────────────────────────────────────
def create_campaign(site_id: int, name: str, strategy: str,
                    segments: list[str] | None = None,
                    limit: int | None = None) -> dict[str, Any]:
    """Create a campaign and lay down its initial schedule."""
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy must be one of {STRATEGIES}")

    site = _site(site_id)
    recipients = email_sender.eligible_recipients(site_id, segments, limit)

    row = db.fetch_one(
        """
        INSERT INTO campaigns (site_id, name, strategy, status, audience_filter)
        VALUES (:site_id, :name, :strategy, 'draft', CAST(:filt AS jsonb))
        RETURNING id
        """,
        site_id=site_id, name=name, strategy=strategy,
        filt=json.dumps({"segments": segments or [], "limit": limit}),
    )
    campaign_id = int(row["id"])
    now = datetime.now(timezone.utc)

    # Module 4's highest-scoring email asset for this site, if one exists.
    # Fetched once rather than per recipient — it is the same copy for everyone
    # at this step, and the personalisation happens in the greeting.
    from api.services import content as content_svc
    generated = content_svc.best_asset(site_id, "email")

    for recipient in recipients:
        if strategy == "fixed":
            # The whole sequence is committed up front — simple to reason about,
            # but blind to how the recipient reacts.
            for i, step in enumerate(STEPS):
                # Only the opener uses generated copy; later steps keep their
                # distinct purpose (social proof, discount, reminder).
                _queue_send(campaign_id, recipient, step, site,
                            now + timedelta(days=step["day"]), i,
                            generated if i == 0 else None)

        elif strategy == "trigger":
            # Only the opener. Everything after it is decided by behaviour, in
            # advance_triggers().
            _queue_send(campaign_id, recipient, STEPS[0], site, now, 0, generated)

        else:  # hybrid
            opener = dict(STEPS[0])
            override = HYBRID_OPENERS.get(recipient.get("segment_name") or "")
            if override:
                opener.update(override)
            # Segment override wins over generated copy: knowing who someone
            # is beats generic site copy, even well-scored generic site copy.
            _queue_send(campaign_id, recipient, opener, site, now, 0,
                        None if override else generated)

    log.info("campaign %s (%s): %s recipients", campaign_id, strategy, len(recipients))

    return {
        "campaign_id": campaign_id,
        "name": name,
        "strategy": strategy,
        "recipients": len(recipients),
        "segments": segments or "all",
        "operational_complexity": POLICY_RULE_COUNT[strategy],
        "scheduled_messages": len(STEPS) * len(recipients) if strategy == "fixed"
                              else len(recipients),
        "note": (
            "No eligible recipients — only visitors who explicitly opted in can "
            "be emailed." if not recipients else None
        ),
    }


# ── Behaviour-driven continuation ────────────────────────────────────────────
def advance_triggers(campaign_id: int, silence_days: int = 2) -> dict[str, Any]:
    """Queue each recipient's next message based on what they actually did.

    The four rules that make up the trigger policy:

        clicked            → the discount / conversion message
        opened, no click   → more product detail
        silent for N days  → a reminder
        converted          → stop (nothing is queued)
    """
    campaign = db.fetch_one(
        "SELECT id, site_id, strategy FROM campaigns WHERE id = :i", i=campaign_id)
    if campaign is None:
        raise ValueError(f"Campaign {campaign_id} not found")
    if campaign["strategy"] == "fixed":
        return {"queued": 0, "reason": "fixed workflow does not react to behaviour"}

    site = _site(campaign["site_id"])

    # Latest state per recipient, from observed interactions only.
    states = db.fetch_all(
        """
        SELECT v.id AS visitor_id, v.email, v.name,
               s.segment_name,
               max(i.occurred_at) FILTER (WHERE i.event_type = 'sent')    AS last_sent,
               count(*)           FILTER (WHERE i.event_type = 'open')    AS opens,
               count(*)           FILTER (WHERE i.event_type = 'click')   AS clicks,
               count(*)           FILTER (WHERE i.event_type = 'convert') AS conversions,
               max(sd.step)                                               AS last_step
        FROM interactions i
        JOIN visitors v      ON v.id = i.visitor_id
        JOIN campaign_sends sd ON sd.id = i.send_id
        LEFT JOIN user_segments s ON s.visitor_id = v.id
        WHERE i.campaign_id = :cid
          AND v.email_consent = TRUE AND v.unsubscribed_at IS NULL
        GROUP BY v.id, s.segment_name
        """,
        cid=campaign_id,
    )

    now = datetime.now(timezone.utc)
    queued = {"clicked": 0, "opened": 0, "silent": 0, "converted_stopped": 0}

    for state in states:
        # Never queue two messages at once for the same person.
        pending = db.fetch_one(
            """SELECT 1 AS ok FROM campaign_sends
               WHERE campaign_id=:cid AND visitor_id=:vid AND status='scheduled'
               LIMIT 1""",
            cid=campaign_id, vid=state["visitor_id"])
        if pending:
            continue

        if state["conversions"]:
            queued["converted_stopped"] += 1
            continue

        next_step = int(state["last_step"] or 0) + 1
        if next_step >= len(STEPS):
            continue

        if state["clicks"]:
            step, bucket = STEP_BY_KEY["discount"], "clicked"
        elif state["opens"]:
            step, bucket = STEP_BY_KEY["product_info"], "opened"
        else:
            last_sent = state["last_sent"]
            if last_sent is None or (now - last_sent) < timedelta(days=silence_days):
                continue
            step, bucket = STEP_BY_KEY["final_reminder"], "silent"

        _queue_send(campaign_id, state, step, site, now, next_step)
        queued[bucket] += 1

    total = sum(v for k, v in queued.items() if k != "converted_stopped")
    log.info("campaign %s: queued %s follow-ups %s", campaign_id, total, queued)
    return {"queued": total, "breakdown": queued}


# ── Reporting ────────────────────────────────────────────────────────────────
def campaign_metrics(campaign_id: int) -> dict[str, Any]:
    """Funnel and rates for one campaign, from observed interactions."""
    # Scalar subqueries, not joins. Joining campaign_sends and interactions on
    # campaign_id alone multiplies them together (16 sends × 16 interactions
    # reported as 256 sends), because the two tables are siblings rather than
    # parent and child at that grain.
    row = db.fetch_one(
        """
        SELECT c.id, c.name, c.strategy, c.status, c.created_at,
          (SELECT count(DISTINCT visitor_id) FROM campaign_sends
            WHERE campaign_id = c.id)                                   AS recipients,
          (SELECT count(*) FROM campaign_sends
            WHERE campaign_id = c.id AND status = 'scheduled')          AS pending,
          (SELECT count(*) FROM interactions
            WHERE campaign_id = c.id AND event_type = 'sent')           AS sent,
          (SELECT count(*) FROM interactions
            WHERE campaign_id = c.id AND event_type = 'open')           AS opens,
          (SELECT count(*) FROM interactions
            WHERE campaign_id = c.id AND event_type = 'click')          AS clicks,
          (SELECT count(*) FROM interactions
            WHERE campaign_id = c.id AND event_type = 'convert')        AS conversions,
          (SELECT count(*) FROM interactions
            WHERE campaign_id = c.id AND event_type = 'unsubscribe')    AS unsubscribes,
          (SELECT count(*) FROM interactions
            WHERE campaign_id = c.id AND source = 'live')               AS live_events,
          (SELECT count(*) FROM interactions
            WHERE campaign_id = c.id AND source = 'dataset')            AS dataset_events
        FROM campaigns c
        WHERE c.id = :cid
        """,
        cid=campaign_id,
    )
    if row is None:
        raise ValueError(f"Campaign {campaign_id} not found")

    sent = row["sent"] or 0
    rate = lambda n: round((n or 0) / sent, 4) if sent else 0.0  # noqa: E731

    # Say plainly what these numbers rest on. A rate computed over the
    # reconstructed research audience is a controlled experiment, not a
    # measurement of live behaviour, and the difference has to survive all the
    # way to the report.
    live, dataset = row["live_events"] or 0, row["dataset_events"] or 0
    if live and dataset:
        basis = "mixed"
    elif dataset:
        basis = "dataset"
    elif live:
        basis = "live"
    else:
        basis = "no data yet"

    return {
        **row,
        "open_rate": rate(row["opens"]),
        "click_through_rate": rate(row["clicks"]),
        "conversion_rate": rate(row["conversions"]),
        "unsubscribe_rate": rate(row["unsubscribes"]),
        "conversions_per_1000_sends": round((row["conversions"] or 0) / sent * 1000, 2)
                                      if sent else 0.0,
        "operational_complexity": POLICY_RULE_COUNT.get(row["strategy"]),
        "data_basis": basis,
        "caveat": (
            "Open rate under-reports: most mail clients block the tracking pixel "
            "by default. Click-through is the reliable engagement signal."
        ),
    }


def compare_strategies(site_id: int) -> list[dict[str, Any]]:
    """Side-by-side comparison of every strategy run for this site.

    This is the live-data counterpart to Module 2's simulated strategy
    comparison — the same metrics, measured rather than modelled.
    """
    campaigns = db.fetch_all(
        "SELECT id FROM campaigns WHERE site_id = :s ORDER BY created_at", s=site_id)
    return [campaign_metrics(int(c["id"])) for c in campaigns]
