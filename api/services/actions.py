"""The Action Plan — what this platform actually delivers to a company.

The system is an **advisor**, not a mailing house. It does not publish to
Instagram and it does not have to send the email. It reads the company's own
website, segments that website's real visitors, works out what to do next, and
hands over a prioritised list of concrete actions with the content already
written:

    "Send this email — subject and body ready — to these 15 High Intent
     contacts, because they clicked but have not converted."

    "Post this on LinkedIn. It carries 24% of attributed credit and is the
     platform you can actually publish to."

That is Figure 5.4 of the report: the *Recommendation Generator* feeding
Module 2 (campaigns) and Module 4 (content). Sending remains available as an
optional connected feature for companies that configure SMTP — see
`email_sender` — but it is not what the product is.

Why an advisory plan still measures results
-------------------------------------------
Every action carries a tracked link, and the link lives in the *content*, not
in the delivery. Whoever puts the message in the envelope — Mailchimp, Gmail,
the company's own social scheduler — the link is still ours:

    email  → /track/click/{token}/{i}   → click recorded → redirect
    social → /l/{token}                 → click recorded → redirect with UTM

The UTM on the social redirect is what makes a published post attributable:
`mos.js` records `utm_source=instagram` on the visitor, and the existing
attribution model already treats that as the acquisition touch. So the loop
closes without this platform ever publishing anything.
"""

from __future__ import annotations

import logging
import secrets
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse

from api import db
from api.services import campaigns as campaign_svc
from api.services import content as content_svc
from api.services import email_sender
from api.settings import get_settings

log = logging.getLogger("mos.actions")

# Platforms a company publishes to by hand. Email is handled separately
# because it is addressed to named people rather than broadcast.
POST_PLATFORMS = ["instagram", "linkedin", "shorts", "facebook"]

# Lower sorts first.
PRIORITY_EMAIL = 10
PRIORITY_POST = 50


def _site(site_id: int) -> dict:
    row = db.fetch_one(
        "SELECT id, name, url, product_name FROM sites WHERE id = :i", i=site_id)
    if row is None:
        raise ValueError(f"Site {site_id} not found")
    return row


def _tracked_target(url: str, platform: str, plan_id: int | None) -> str:
    """Append UTM parameters so a published post becomes attributable.

    This is the entire trick behind advisory-but-measurable: we cannot see the
    post, but we can see the visit it produced, because the link the company
    pastes carries its origin.
    """
    parts = urlparse(url)
    params = urlencode({
        "utm_source": platform,
        "utm_medium": "social",
        "utm_campaign": f"plan-{plan_id}" if plan_id else "plan",
    })
    query = f"{parts.query}&{params}" if parts.query else params
    return urlunparse(parts._replace(query=query))


# ── Building a plan ──────────────────────────────────────────────────────────

def build_plan(site_id: int, strategy: str = "hybrid",
               segments: list[str] | None = None,
               limit: int | None = None) -> dict[str, Any]:
    """Produce the next set of recommended actions for a site.

    Email actions come from the campaign engine (which is where the fixed /
    trigger / hybrid research comparison lives — the three policies differ in
    how many actions they plan and on what evidence). Post actions come from
    the generated content assets, ordered by what attribution says is worth
    publishing to.
    """
    site = _site(site_id)

    # ── Email half: reuse the tested campaign planner. It writes drafts into
    # campaign_sends with tracked links already rewritten. Nothing is sent.
    plan = campaign_svc.create_campaign(
        site_id, f"Plan · {strategy}", strategy, segments, limit)
    plan_id = plan["campaign_id"]

    reachable = len(email_sender.eligible_recipients(site_id, segments))
    db.execute(
        """
        UPDATE campaign_sends
        SET rationale = :r
        WHERE campaign_id = :c AND rationale IS NULL
        """,
        c=plan_id,
        r=(f"{reachable} of this site's visitors have explicitly opted in to "
           f"email. The {strategy} policy decides how many messages each of "
           f"them is planned for and on what evidence."),
    )

    # ── Post half: one action per platform worth publishing to.
    # Deliberately non-fatal. The email half of a plan is independently useful,
    # and content generation depends on a crawl and on model artifacts that may
    # legitimately be unavailable. Losing the whole plan — and stranding the
    # drafts already written above — would be the worse failure.
    try:
        posts = _build_post_actions(site_id, plan_id, site)
        post_error = None
    except Exception as exc:  # noqa: BLE001 — reported, not swallowed
        log.exception("post actions failed for site %s", site_id)
        posts, post_error = [], f"{type(exc).__name__}: {exc}"

    counts = db.fetch_one(
        "SELECT count(*) AS n FROM campaign_sends WHERE campaign_id = :c",
        c=plan_id)

    result = {
        "plan_id": plan_id,
        "strategy": strategy,
        "email_actions": counts["n"],
        "post_actions": len(posts),
        "reachable": reachable,
        "operational_complexity": campaign_svc.POLICY_RULE_COUNT.get(strategy),
    }
    if post_error:
        result["post_actions_error"] = post_error
        result["note"] = ("Email actions were planned; post actions could not "
                          "be generated. Generate content for this site first.")
    return result


def _build_post_actions(site_id: int, plan_id: int, site: dict) -> list[dict]:
    """One post action per platform, best generated asset first.

    Platforms are ordered by the linear attribution model, but only across the
    channels a company can actually publish to. Attribution frequently hands
    most of the credit to `direct` or `google`, and telling someone to "post
    more direct traffic" is not advice.
    """
    priorities = content_svc.platform_priorities(site_id)
    # `actionable_ranking` is {platform: credit}, already ordered by credit.
    credit: dict[str, float] = priorities.get("actionable_ranking") or {}
    ordered = [p for p in credit if p in POST_PLATFORMS]
    # Platforms with no attribution signal still get an action — that is how a
    # cold-start site starts generating a signal at all.
    ordered += [p for p in POST_PLATFORMS if p not in ordered]

    created: list[dict] = []
    for position, platform in enumerate(ordered):
        asset = content_svc.best_asset(site_id, platform)
        if asset is None:
            continue  # nothing generated for this platform yet

        share = credit.get(platform)
        if share:
            why = (f"{platform.title()} carries {share * 100:.0f}% of the "
                   "attributed credit among the channels you can publish to.")
        else:
            why = (f"No attribution signal for {platform} yet — this post is "
                   "how you start generating one.")

        token = secrets.token_urlsafe(20)
        row = db.fetch_one(
            """
            INSERT INTO content_actions
                (site_id, campaign_id, content_asset_id, platform,
                 target_segment, audience_size, rationale, priority,
                 track_token, target_url)
            VALUES (:s, :c, :a, :p, :seg, :n, :why, :prio, :tok, :url)
            RETURNING id
            """,
            s=site_id, c=plan_id, a=asset["id"], p=platform,
            seg=asset.get("target_segment"), n=0, why=why,
            prio=PRIORITY_POST + position, tok=token,
            url=_tracked_target(site["url"], platform, plan_id),
        )
        created.append({"id": row["id"], "platform": platform})

    return created


# ── Reading the plan ─────────────────────────────────────────────────────────

def current_plan(site_id: int, include_done: bool = False) -> dict[str, Any]:
    """Everything the company should do next, content included.

    Email drafts are grouped by message rather than listed per recipient: a
    marketer wants "send this to these 15 people", not fifteen near-identical
    rows.
    """
    settings = get_settings()
    base = settings.public_api_url.rstrip("/")
    done_filter = "" if include_done else "AND cs.status = 'scheduled'"

    email_rows = db.fetch_all(
        f"""
        SELECT cs.campaign_id, cs.step, cs.subject,
               min(cs.body_text) AS body_text,
               min(cs.rationale) AS rationale,
               count(*)          AS audience_size,
               min(cs.scheduled_for) AS scheduled_for,
               bool_and(v.source = 'dataset') AS all_dataset,
               c.strategy
        FROM campaign_sends cs
        JOIN campaigns c ON c.id = cs.campaign_id
        JOIN visitors  v ON v.id = cs.visitor_id
        WHERE c.site_id = :s {done_filter}
        GROUP BY cs.campaign_id, cs.step, cs.subject, c.strategy
        ORDER BY min(cs.scheduled_for) NULLS FIRST, cs.step
        """,
        s=site_id,
    )

    emails = [{
        "kind": "email",
        "campaign_id": r["campaign_id"],
        "step": r["step"],
        "strategy": r["strategy"],
        "subject": r["subject"],
        "body": r["body_text"],
        "audience_size": r["audience_size"],
        "rationale": r["rationale"],
        "scheduled_for": r["scheduled_for"],
        "dataset_audience": r["all_dataset"],
        "priority": PRIORITY_EMAIL + (r["step"] or 0),
    } for r in email_rows]

    post_filter = "" if include_done else "AND a.status = 'suggested'"
    post_rows = db.fetch_all(
        f"""
        SELECT a.id, a.platform, a.rationale, a.priority, a.track_token,
               a.target_url, a.status, a.executed_at,
               ca.caption, ca.hashtags, ca.cta, ca.image_prompt, ca.subject,
               ca.final_score::float8 AS final_score, ca.target_segment
        FROM content_actions a
        LEFT JOIN content_assets ca ON ca.id = a.content_asset_id
        WHERE a.site_id = :s {post_filter}
        ORDER BY a.priority, a.id
        """,
        s=site_id,
    )

    posts = [{
        "kind": "post",
        "id": r["id"],
        "platform": r["platform"],
        "caption": r["caption"],
        "hashtags": r["hashtags"] or [],
        "cta": r["cta"],
        "image_brief": r["image_prompt"],
        "rationale": r["rationale"],
        "priority": r["priority"],
        "status": r["status"],
        "executed_at": r["executed_at"],
        # The link to paste. It records the click and tags the visit with its
        # platform, which is what makes a hand-published post measurable.
        "tracked_link": f"{base}/l/{r['track_token']}",
        "final_score": r["final_score"],
    } for r in post_rows]

    actions = sorted(emails + posts, key=lambda a: a["priority"])

    # What this website can actually do, and therefore which recommendations are
    # even offerable. Shown rather than silently applied: "no premium offer
    # because the site has no checkout" is useful for an operator to read, and
    # it makes the capability detection auditable instead of invisible.
    from api.services import actions_catalogue as catalogue
    from api.services import content as content_svc

    capabilities = content_svc.site_capabilities(site_id)
    offerable = catalogue.site_actions(capabilities)

    return {
        "site_id": site_id,
        "actions": actions,
        "counts": {"email": len(emails), "post": len(posts),
                   "total": len(actions)},
        "capabilities": capabilities,
        "offerable_actions": [catalogue.describe(k) for k in offerable],
        "withheld_actions": [
            w for w in catalogue.withheld(capabilities, {})
            if w["scope"] == "site"
        ],
        "how_to_use": (
            "This platform advises, it does not publish. Copy each piece of "
            "content into your own email tool or social account. Keep the "
            "tracked links exactly as they are — that is how clicks and "
            "conversions still get measured after you publish."
        ),
    }


# ── Marking work done ────────────────────────────────────────────────────────

def mark_post_executed(action_id: int, executed: bool = True,
                       notes: str | None = None) -> dict[str, Any]:
    row = db.fetch_one(
        """
        UPDATE content_actions
        SET status      = :st,
            executed_at = CASE WHEN :ex THEN now() ELSE NULL END,
            -- CAST(...) rather than ::text — SQLAlchemy reads `:notes::text`
            -- as a malformed parameter name and the statement never compiles.
            outcome     = CASE WHEN CAST(:notes AS text) IS NULL THEN outcome
                               ELSE outcome || jsonb_build_object(
                                        'notes', CAST(:notes AS text)) END
        WHERE id = :i
        RETURNING id, platform, status, executed_at
        """,
        i=action_id, st="executed" if executed else "skipped",
        ex=executed, notes=notes,
    )
    if row is None:
        raise ValueError(f"Action {action_id} not found")
    return row


def mark_email_executed(campaign_id: int, step: int,
                        executed: bool = True) -> dict[str, Any]:
    """Record that the company sent this message from their own tool.

    A `sent` interaction is written so the funnel still starts somewhere — but
    it is self-reported, not observed, and `source` is derived from the
    recipients' provenance exactly as everywhere else in the system.
    """
    status = "executed" if executed else "skipped"
    rows = db.fetch_all(
        """
        UPDATE campaign_sends
        SET status = :st, executed_at = CASE WHEN :ex THEN now() ELSE NULL END
        WHERE campaign_id = :c AND step = :step AND status = 'scheduled'
        RETURNING id, visitor_id
        """,
        c=campaign_id, step=step, st=status, ex=executed,
    )

    if executed and rows:
        camp = db.fetch_one(
            "SELECT site_id, strategy FROM campaigns WHERE id = :i", i=campaign_id)
        db.execute_many(
            """
            INSERT INTO interactions
                (site_id, visitor_id, campaign_id, send_id, strategy, channel,
                 platform, event_type, source, meta)
            VALUES (:site_id, :visitor_id, :campaign_id, :send_id, :strategy,
                    'email', 'email', 'sent',
                    -- Derived, never asserted: a dataset-derived visitor can
                    -- never produce a row that claims to be live observation.
                    (SELECT source FROM visitors WHERE id = :visitor_id),
                    CAST('{"self_reported": true}' AS jsonb))
            """,
            [{"site_id": camp["site_id"], "strategy": camp["strategy"],
              "visitor_id": r["visitor_id"], "campaign_id": campaign_id,
              "send_id": r["id"]} for r in rows],
        )

    return {"campaign_id": campaign_id, "step": step,
            "status": status, "messages": len(rows)}


def email_recipients(campaign_id: int, step: int, limit: int = 500) -> dict:
    """Exactly who a queued email action goes to — name, email, segment.

    The Action Plan summarises an email action as "send to N contacts"; this
    is the N spelled out, so the marketer can see and verify the actual list
    before sending. Ordered by segment so the grouping is visible at a glance.
    """
    total = db.fetch_one(
        """
        SELECT count(*) AS n FROM campaign_sends
        WHERE campaign_id = :c AND step = :st
        """,
        c=campaign_id, st=step)
    rows = db.fetch_all(
        """
        SELECT v.name, v.email, us.segment_name, cs.status
        FROM campaign_sends cs
        JOIN visitors v            ON v.id = cs.visitor_id
        LEFT JOIN user_segments us ON us.visitor_id = v.id
        WHERE cs.campaign_id = :c AND cs.step = :st
        ORDER BY us.segment_name NULLS LAST, v.email NULLS LAST
        LIMIT :lim
        """,
        c=campaign_id, st=step, lim=limit)
    return {
        "total": (total or {}).get("n", 0),
        "recipients": [{
            "name": r["name"],
            "email": r["email"],
            "segment": r["segment_name"],
            "status": r["status"],
        } for r in rows],
    }
