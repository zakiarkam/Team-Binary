"""Module 4 as a service — read the client's website, then write for it.

Until now the system asked for a website URL and never opened it: content was
generated from the typed brief alone. This closes that gap. The flow is

    crawl the site  →  derive the brief from its own copy
                    →  generate per-platform assets (Module 4)
                    →  score them (engagement · semantic · platform fit)
                    →  persist to content_assets  (report Figure 5.5)

and the platform *order* comes from Module 3's attribution, so the channels
that actually earn conversions are written for first. That is the closed loop
in Figure 5.1, running on this site's own numbers rather than on fixtures.

Crawling is cached in `site_crawls`: a marketing site changes far more slowly
than a campaign is generated, and re-fetching on every request would be rude to
the client's server and slow for the operator.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from api import db

log = logging.getLogger("mos.content")

#: How long a crawl stays fresh. Marketing copy rarely changes hourly.
CRAWL_TTL_HOURS = 24

#: Platforms the content engine can write for.
#:
#: Owned by Module 4, not redeclared here: the generator's per-platform specs,
#: tone registers and creative briefs are what make a channel writable, so the
#: list of writable channels has to come from the same file as those rules.
#: `api.main` puts modules/m4_content on sys.path before the routers import.
try:
    import config as _m4_config

    SUPPORTED_PLATFORMS = list(_m4_config.SERVICE_PLATFORMS)
except Exception:  # standalone import, m4 not on the path
    SUPPORTED_PLATFORMS = ["email", "instagram", "linkedin", "shorts", "facebook"]


# ── Crawling ─────────────────────────────────────────────────────────────────
def latest_crawl(site_id: int, max_age_hours: int = CRAWL_TTL_HOURS) -> dict | None:
    row = db.fetch_one(
        """
        SELECT data, ok, crawled_at FROM site_crawls
        WHERE site_id = :s AND crawled_at > now() - make_interval(hours => :h)
        ORDER BY crawled_at DESC LIMIT 1
        """,
        s=site_id, h=max_age_hours,
    )
    if row is None or not row["ok"]:
        return None
    return row["data"]


def site_capabilities(site_id: int, max_age_hours: int = 24 * 30) -> dict[str, bool]:
    """What this website can do, pooled across every page we have crawled.

    Capability belongs to the *site*, not to a page. The basket page of a shop
    does not itself link to a basket, so judging from one page under-reports —
    a storefront looks transactional and its own checkout does not. Pooling with
    OR across recent crawls means evidence accumulates and never disappears
    because the last crawl happened to land somewhere quiet.

    Asymmetric on purpose: seeing a checkout once is proof the site has one;
    not seeing it on a given page proves nothing.
    """
    rows = db.fetch_all(
        """
        SELECT data FROM site_crawls
        WHERE site_id = :s AND ok
          AND crawled_at > now() - make_interval(hours => :h)
        ORDER BY crawled_at DESC LIMIT 20
        """,
        s=site_id, h=max_age_hours,
    )

    pooled: dict[str, bool] = {}
    for row in rows:
        for name, present in ((row["data"] or {}).get("capabilities") or {}).items():
            pooled[name] = pooled.get(name, False) or bool(present)
    return pooled


def crawl_site(site_id: int, force: bool = False) -> dict[str, Any]:
    """Fetch the site's marketing copy, caching the result.

    A failed crawl is recorded rather than raised: an unreachable site should
    degrade content generation to the typed brief, not break the campaign.
    """
    site = db.fetch_one("SELECT id, url, name FROM sites WHERE id = :i", i=site_id)
    if site is None:
        raise ValueError(f"Site {site_id} not found")

    if not force:
        cached = latest_crawl(site_id)
        if cached is not None:
            return {"data": cached, "cached": True, "url": site["url"]}

    import crawler   # imported lazily — pulls in playwright

    log.info("crawling %s", site["url"])
    try:
        data = crawler.crawl_website(site["url"])
        ok = data.get("status") != "failed"
    except Exception as exc:                       # network, DNS, browser, …
        log.warning("crawl of %s failed: %s", site["url"], exc)
        data, ok = {"status": "failed", "error": str(exc)[:500]}, False

    db.execute(
        """INSERT INTO site_crawls (site_id, url, ok, data)
           VALUES (:s, :u, :ok, CAST(:d AS jsonb))""",
        s=site_id, u=site["url"], ok=ok, d=json.dumps(data, default=str),
    )

    return {
        "data": data if ok else None,
        "cached": False,
        "ok": ok,
        "url": site["url"],
        "error": None if ok else data.get("error"),
        "extracted": {
            "headings": len(data.get("headings", [])),
            "paragraphs": len(data.get("paragraphs", [])),
            "ctas": len(data.get("cta_texts", [])),
        } if ok else {},
    }


# ── Feedback from analytics ──────────────────────────────────────────────────
def platform_priorities(site_id: int) -> dict[str, Any]:
    """Rank platforms by the conversion credit Module 3 attributed to them.

    This is the analytics → content half of the closed loop. Where there is not
    enough evidence yet, it says so and leaves the order alone rather than
    inventing a ranking from three conversions.
    """
    from api.services import analytics

    attribution = analytics.build_attribution(site_id, level="platform")
    models = attribution.get("models") or {}

    # Linear multi-touch is the fairest single ranking to act on: first-touch
    # over-credits acquisition and last-touch over-credits whatever closed.
    ranking_rows = models.get("linear") or models.get("markov") or []
    if not isinstance(ranking_rows, list) or not ranking_rows:
        # Same keys as the populated case. A response whose shape depends on how
        # much data exists forces every caller to special-case the empty state,
        # and the empty state is the normal one for a newly launched product.
        return {
            "platform_ranking": {},
            "actionable_ranking": {},
            "unactionable_channels": {},
            "actionable_share": 0.0,
            "basis": "none",
            "converters": attribution.get("converters", 0),
            "data_basis": attribution.get("data_basis"),
            "diagnostics": attribution.get("diagnostics"),
            "note": attribution.get("note")
                    or "Not enough converting journeys to rank platforms yet.",
        }

    ranking = {
        str(r["platform"]): round(float(r["credit"]), 4)
        for r in ranking_rows if r.get("platform")
    }
    ordered = dict(sorted(ranking.items(), key=lambda kv: -kv[1]))

    # Attribution ranks every channel a visitor arrived through, including ones
    # this system cannot publish to — "direct" and "google" are acquisition
    # channels, not places to post content. Splitting them out keeps the loop
    # honest: only part of the attributed credit is actually actionable here,
    # and a ranking that quietly drops the rest would overstate the feedback.
    actionable = {k: v for k, v in ordered.items() if k in SUPPORTED_PLATFORMS}
    unactionable = {k: v for k, v in ordered.items() if k not in SUPPORTED_PLATFORMS}
    total = sum(ordered.values()) or 1.0

    return {
        "platform_ranking": ordered,
        "actionable_ranking": actionable,
        "unactionable_channels": unactionable,
        "actionable_share": round(sum(actionable.values()) / total, 3),
        "basis": "linear multi-touch attribution",
        "converters": attribution.get("converters"),
        "data_basis": attribution.get("data_basis"),
        "diagnostics": attribution.get("diagnostics"),
        "note": (
            f"{round(sum(unactionable.values()) / total * 100)}% of attributed "
            f"credit sits with channels this system cannot publish to "
            f"({', '.join(unactionable) or 'none'}); only the remainder can "
            "influence what gets written."
        ) if unactionable else None,
    }


def _ordered_platforms(requested: list[str], priorities: dict) -> list[str]:
    """Put the platforms that earn conversions first, keeping the rest."""
    ranking = priorities.get("platform_ranking") or {}
    if not ranking:
        return requested
    return sorted(requested, key=lambda p: -ranking.get(p, 0.0))


# ── Generation ───────────────────────────────────────────────────────────────
def generate_for_site(site_id: int, platforms: list[str] | None = None,
                      engine: str = "fast", campaign_id: int | None = None,
                      use_website: bool = True) -> dict[str, Any]:
    """Generate, score and store platform content for a site."""
    site = db.fetch_one(
        """SELECT id, name, url, product_name, description, target_audience
           FROM sites WHERE id = :i""", i=site_id)
    if site is None:
        raise ValueError(f"Site {site_id} not found")

    website_data = None
    crawl_status = "skipped"
    if use_website:
        crawl = crawl_site(site_id)
        website_data = crawl.get("data")
        crawl_status = "cached" if crawl.get("cached") else (
            "fetched" if website_data else "failed")

    priorities = platform_priorities(site_id)
    requested = platforms or SUPPORTED_PLATFORMS
    ordered = _ordered_platforms(requested, priorities)

    brief = {
        "product_name": site["product_name"] or site["name"],
        "website_url": site["url"],
        "target_audience": site["target_audience"] or "modern teams",
        "customer_segment": "",
        "product_description": site["description"] or "",
        "preferred_platforms": ordered,
    }

    import content_service

    result = content_service.generate(
        brief, priorities=None, engine=engine, website_data=website_data)

    assets = result["assets"]
    summary = result["summary"]

    rows = [{
        "site_id": site_id,
        "campaign_id": campaign_id,
        "platform": a["platform"],
        "subject": _subject_for(a, summary),
        "caption": a.get("caption", ""),
        "hashtags": json.dumps(a.get("hashtags") or []),
        "cta": a.get("cta", ""),
        # A video platform returns `shorts_prompt`, an image platform
        # `image_prompt`. Both are creative briefs, so they share a column —
        # but which medium it is has to travel with it, or the dashboard shows
        # a video brief labelled as an image brief.
        "image_prompt": a.get("image_prompt") or a.get("shorts_prompt") or "",
        "visual_kind": "video" if (a.get("shorts_prompt") or "").strip() else "image",
        "campaign_goal": summary.get("campaign_goal"),
        # The tone this asset was actually written in — the brand voice adapted
        # to the platform's register. Falls back to the campaign-wide brand tone
        # for assets generated before the register layer existed.
        "tone": a.get("platform_tone") or summary.get("tone"),
        "brand_tone": a.get("brand_tone") or summary.get("tone"),
        "engagement": _f(a.get("engagement_score")),
        "semantic": _f(a.get("semantic_score")),
        "platform_fit": _f(a.get("platform_suitability_score")),
        "final": _f(a.get("final_score")),
        "engine": engine,
    } for a in assets]

    if rows:
        db.execute_many(
            """
            INSERT INTO content_assets (site_id, campaign_id, platform, subject,
                                        caption, hashtags, cta, image_prompt,
                                        visual_kind, campaign_goal, tone,
                                        brand_tone,
                                        engagement_score, semantic_score,
                                        platform_suitability_score,
                                        final_score, engine)
            VALUES (:site_id, :campaign_id, :platform, :subject, :caption,
                    CAST(:hashtags AS jsonb), :cta, :image_prompt,
                    :visual_kind, :campaign_goal, :tone, :brand_tone,
                    :engagement, :semantic,
                    :platform_fit, :final, :engine)
            """,
            rows,
        )

    db.execute(
        """INSERT INTO pipeline_runs (site_id, stage, status, detail, finished_at)
           VALUES (:s, 'content', 'ok', CAST(:d AS jsonb), now())""",
        s=site_id,
        d=json.dumps({"assets": len(rows), "engine": engine,
                      "content_source": result["content_source"]}),
    )

    return {
        "site_id": site_id,
        "assets": assets,
        "n_assets": len(assets),
        "engine": engine,
        "content_source": result["content_source"],
        "crawl": crawl_status,
        "campaign_goal": summary.get("campaign_goal"),
        # Campaign-level, so this is the brand voice. The per-platform register
        # it was spoken in rides on each asset's `platform_tone`.
        "tone": summary.get("tone"),
        "brand_tone": summary.get("tone"),
        "site_keywords": summary.get("site_keywords", []),
        "platform_order": ordered,
        "priorities": priorities,
        "note": (
            "Copy was written from the product's own website."
            if result["content_source"] == "website"
            else "The website could not be read, so copy came from the brief."
        ),
    }


#: A leading "Subject: ..." line inside the generated email body.
_SUBJECT_LINE = re.compile(r"^\s*subject\s*:\s*(.+?)\s*$", re.IGNORECASE)

#: A salutation prefix such as "Hi busy founders — " or "Hello there,".
#: Bounded and anchored so it can only ever remove an actual greeting, never
#: swallow a sentence that happens to begin with "Hi".
_GREETING_PREFIX = re.compile(
    r"^(hi|hello|hey|dear)\b[^\n]{0,60}?\s*[—–,:-]\s+", re.IGNORECASE)


def split_email_asset(caption: str) -> tuple[str | None, str]:
    """Separate a generated email into its subject line and its body.

    The content engine writes email as a *complete* message — a "Subject:" line
    and its own salutation — whereas `email_sender.compose()` supplies the
    greeting and the wrapper. Pasting one into the other produced
    "Subject: Subject: …" and two greetings in a row, so the parts are
    separated here instead.
    """
    subject: str | None = None
    lines = (caption or "").strip().splitlines()

    if lines:
        match = _SUBJECT_LINE.match(lines[0])
        if match:
            subject = match.group(1).strip()
            lines = lines[1:]

    body = "\n".join(lines).strip()
    body = _GREETING_PREFIX.sub("", body, count=1)
    return subject, body


def _subject_for(asset: dict, summary: dict) -> str | None:
    """Email needs a subject line; social platforms do not."""
    if asset.get("platform") != "email":
        return None

    subject, body = split_email_asset(asset.get("caption") or "")
    if not subject:
        first_line = body.splitlines()[0] if body else ""
        subject = first_line[:78].rstrip(" .,-—")
    return (subject or f"{summary.get('product_name', 'Hello')} — a quick note")[:120]


def _f(value: Any) -> float | None:
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


# ── Reading back ─────────────────────────────────────────────────────────────
def list_assets(site_id: int, platform: str | None = None,
                limit: int = 50) -> dict[str, Any]:
    rows = db.fetch_all(
        f"""
        SELECT id, platform, subject, caption, hashtags, cta, image_prompt,
               visual_kind, campaign_goal, tone, brand_tone,
               engagement_score::float8          AS engagement_score,
               semantic_score::float8            AS semantic_score,
               platform_suitability_score::float8 AS platform_suitability_score,
               final_score::float8               AS final_score,
               engine, created_at
        FROM content_assets
        WHERE site_id = :s {'AND platform = :p' if platform else ''}
        ORDER BY created_at DESC, final_score DESC
        LIMIT :lim
        """,
        s=site_id, p=platform, lim=limit,
    )
    return {"assets": rows, "count": len(rows)}


def best_asset(site_id: int, platform: str) -> dict | None:
    """The copy to use for a platform — newest generation first.

    This used to return the highest-scoring asset ever stored, which meant
    regenerating content changed nothing: the action plan and the campaign
    emails kept serving copy from an earlier run whenever that run happened to
    score higher. Two reasons that is the wrong way round.

    An asset is written *from a crawl*. Once the site has been re-read, older
    assets describe an earlier version of the product, so preferring them is
    preferring stale copy however well it scored at the time.

    And the margin that kept them is not meaningful. `final_score` is
    0.40*semantic + 0.40*platform_fit + 0.20*engagement; platform fit saturates
    at 1.0 for anything obeying its spec, so it rarely separates two candidates,
    and the engagement term comes from a regressor measured at R^2 = -0.30 and
    Spearman 0.02 on the only data available (see config.py). Score still picks
    between candidates *within* a run — which is where it is comparing like with
    like — but it no longer outranks recency across runs.
    """
    return db.fetch_one(
        """
        SELECT id, subject, caption, cta, hashtags, image_prompt, visual_kind,
               final_score::float8 AS final_score
        FROM content_assets
        WHERE site_id = :s AND platform = :p
        ORDER BY created_at DESC, final_score DESC NULLS LAST
        LIMIT 1
        """,
        s=site_id, p=platform,
    )
