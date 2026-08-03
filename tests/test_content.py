"""Phase 5 tests — Module 4 content, driven by the client's own website.

The central claim being tested is the one the product makes on its front page:
"give us your website link". Until this phase the URL was collected and never
opened. These tests fail if that regresses.

Requires PostgreSQL:  docker-compose up -d
"""

from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from api import db
from api.main import app
from api.services import content as svc

pytestmark = pytest.mark.skipif(
    not db.ping(), reason="PostgreSQL is not reachable — run `docker-compose up -d`"
)

# A realistic crawl payload, in the shape crawler.crawl_website() returns.
CRAWL = {
    "url": "https://acme.example",
    "title": "Acme Robotics — Warehouse automation",
    "meta_description": "Acme Robotics builds warehouse automation for mid-sized "
                        "distributors who cannot afford a full retrofit.",
    "headings": ["Automate picking without rebuilding", "Deploy in weeks",
                 "Trusted by distributors", "Pricing"],
    "paragraphs": [
        "Acme robots slot into the aisles you already have, so you keep the racking, "
        "the WMS and the team you have spent years training.",
        "Most sites are picking autonomously within three weeks of delivery.",
    ],
    "cta_texts": ["Book a demo", "See pricing", "Read the case study"],
    "image_alt_texts": [], "iframe_links": [],
}


@pytest.fixture(scope="module")
def client() -> TestClient:
    db.init_schema()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def site(client: TestClient):
    res = client.post("/sites", json={
        "name": "Acme Robotics", "url": "https://acme.example",
        "product_name": "Acme Robotics",
        "target_audience": "mid-sized distributors",
    })
    body = res.json()["site"]
    yield body
    db.execute("DELETE FROM sites WHERE id = :i", i=body["id"])


def _cache_crawl(site_id: int, data: dict = CRAWL, ok: bool = True) -> None:
    db.execute(
        """INSERT INTO site_crawls (site_id, url, ok, data)
           VALUES (:s, 'https://acme.example', :ok, CAST(:d AS jsonb))""",
        s=site_id, ok=ok, d=json.dumps(data))


# ── The website actually reaches the copy ────────────────────────────────────

def test_generated_copy_uses_the_websites_own_words(site) -> None:
    """The whole point of Phase 5. If the crawl is ignored, this fails."""
    _cache_crawl(site["id"])
    result = svc.generate_for_site(site["id"], platforms=["linkedin"])

    assert result["content_source"] == "website"
    combined = " ".join(a["caption"] for a in result["assets"]).lower()
    assert "warehouse automation" in combined or "distributors" in combined


def test_hashtags_come_from_the_sites_headings(site) -> None:
    _cache_crawl(site["id"])
    result = svc.generate_for_site(site["id"], platforms=["instagram"])

    assert result["site_keywords"], "headings should yield keywords"
    # "automate", "picking", "deploy", "weeks" … all appear in the headings.
    assert any(k in {"automate", "picking", "deploy", "weeks", "distributors",
                     "trusted", "pricing", "rebuilding"}
               for k in result["site_keywords"])


def test_unreachable_website_degrades_instead_of_failing(site) -> None:
    """A site that is down must not take the campaign down with it."""
    _cache_crawl(site["id"], {"status": "failed", "error": "timeout"}, ok=False)
    result = svc.generate_for_site(site["id"], platforms=["email"],
                                   use_website=False)

    assert result["content_source"] == "brief"
    assert result["n_assets"] == 1
    assert "could not be read" in result["note"] or "brief" in result["note"]


def test_crawls_are_cached(site) -> None:
    _cache_crawl(site["id"])
    assert svc.latest_crawl(site["id"]) is not None
    result = svc.generate_for_site(site["id"], platforms=["email"])
    assert result["crawl"] == "cached"


def test_failed_crawls_are_not_served_from_cache(site) -> None:
    """A cached failure must not masquerade as content."""
    _cache_crawl(site["id"], {"status": "failed"}, ok=False)
    assert svc.latest_crawl(site["id"]) is None


# ── Email asset parsing ──────────────────────────────────────────────────────

def test_email_asset_splits_into_subject_and_body() -> None:
    """Regression: the generated email is a *complete* message. Pasting it into
    the sender produced "Subject: Subject: …" and two greetings."""
    caption = ("Subject: A smarter way to pick\n\n"
               "Hi busy distributors — Acme slots into the aisles you have.")
    subject, body = svc.split_email_asset(caption)

    assert subject == "A smarter way to pick"
    assert not body.lower().startswith("subject")
    assert not body.lower().startswith("hi busy")
    assert "Acme slots into the aisles" in body


def test_split_keeps_sentences_that_merely_start_with_hi() -> None:
    """The greeting stripper must not eat real copy."""
    _, body = svc.split_email_asset("Higher throughput, lower cost.")
    assert body == "Higher throughput, lower cost."


def test_split_handles_an_asset_with_no_subject_line() -> None:
    subject, body = svc.split_email_asset("Straight into the pitch.")
    assert subject is None
    assert body == "Straight into the pitch."


def test_stored_email_subject_is_not_prefixed_with_subject(site) -> None:
    _cache_crawl(site["id"])
    svc.generate_for_site(site["id"], platforms=["email"])

    row = db.fetch_one(
        """SELECT subject FROM content_assets
           WHERE site_id = :s AND platform = 'email'
           ORDER BY id DESC LIMIT 1""", s=site["id"])
    assert row["subject"]
    assert not row["subject"].lower().startswith("subject:")


# ── Persistence (report Figure 5.5) ──────────────────────────────────────────

def test_assets_are_stored_with_all_four_scores(site) -> None:
    _cache_crawl(site["id"])
    svc.generate_for_site(site["id"], platforms=["email", "linkedin"])

    rows = db.fetch_all(
        """SELECT platform, caption, engagement_score, semantic_score,
                  platform_suitability_score, final_score
           FROM content_assets WHERE site_id = :s""", s=site["id"])

    assert len(rows) == 2
    for r in rows:
        assert r["caption"]
        for score in ("engagement_score", "semantic_score",
                      "platform_suitability_score", "final_score"):
            assert r[score] is not None, f"{r['platform']} missing {score}"
            assert 0.0 <= float(r[score]) <= 1.0


def test_best_asset_serves_the_newest_generation(site) -> None:
    """Regenerating content must change what the plan and the emails serve.

    This previously asserted the all-time highest score, which meant a site
    could be re-crawled and rewritten and the action plan would keep handing
    over copy from the earlier run. Assets are written from a crawl, so the
    newest run is the one describing the current site.
    """
    _cache_crawl(site["id"])
    svc.generate_for_site(site["id"], platforms=["email"])
    svc.generate_for_site(site["id"], platforms=["email"])

    best = svc.best_asset(site["id"], "email")
    newest = db.fetch_one(
        """SELECT id FROM content_assets
           WHERE site_id = :s AND platform = 'email'
           ORDER BY created_at DESC, final_score DESC NULLS LAST
           LIMIT 1""", s=site["id"])
    assert best["id"] == newest["id"]


def test_score_still_decides_between_candidates_from_the_same_run(site) -> None:
    """Recency outranks score *across* runs, not within one.

    Within a single generation the candidates are comparable, so the composite
    score is still what picks between them.
    """
    _cache_crawl(site["id"])
    for score in (0.40, 0.90, 0.55):
        db.execute(
            """
            INSERT INTO content_assets (site_id, platform, caption, hashtags,
                                        cta, final_score, created_at)
            VALUES (:s, 'linkedin', :cap, '[]'::jsonb, 'Go', :f,
                    TIMESTAMPTZ '2030-01-01 00:00:00+00')
            """, s=site["id"], cap=f"candidate {score}", f=score)

    best = svc.best_asset(site["id"], "linkedin")
    assert float(best["final_score"]) == 0.90


def test_unsupported_platform_is_rejected(site, client: TestClient) -> None:
    res = client.post(f"/sites/{site['id']}/content/generate",
                      json={"platforms": ["myspace"]})
    assert res.status_code == 400
    assert "myspace" in res.json()["detail"]


# ── The analytics → content half of the loop ─────────────────────────────────

def test_platform_order_follows_attribution(site) -> None:
    """Channels that earn conversions get written for first."""
    priorities = {"platform_ranking": {"linkedin": 0.6, "email": 0.3,
                                       "instagram": 0.1}}
    ordered = svc._ordered_platforms(["email", "instagram", "linkedin"], priorities)
    assert ordered == ["linkedin", "email", "instagram"]


def test_platform_order_is_untouched_without_evidence(site) -> None:
    requested = ["email", "instagram", "linkedin"]
    assert svc._ordered_platforms(requested, {"platform_ranking": {}}) == requested


def test_priorities_declare_how_much_credit_is_actionable(site) -> None:
    """Attribution ranks acquisition channels this system cannot publish to.
    Quietly dropping them would overstate how much feedback reaches content."""
    result = svc.platform_priorities(site["id"])
    assert "actionable_ranking" in result
    assert "unactionable_channels" in result


def test_priorities_decline_without_enough_conversions(site) -> None:
    result = svc.platform_priorities(site["id"])
    assert result["platform_ranking"] == {}
    assert result["note"]


# ── The content → campaign half of the loop ──────────────────────────────────

def test_campaign_uses_generated_copy_when_it_exists(site) -> None:
    """Content generated from the website is what actually gets sent."""
    from api.services import campaigns

    db.execute(
        """INSERT INTO visitors (site_id, visitor_uid, email, email_consent, consent_at)
           VALUES (:s, 'reader', 'reader@x.com', TRUE, now())""", s=site["id"])

    _cache_crawl(site["id"])
    svc.generate_for_site(site["id"], platforms=["email"])

    created = campaigns.create_campaign(site["id"], "Loop", "trigger")
    send = db.fetch_one(
        """SELECT subject, body_text, content_asset_id FROM campaign_sends
           WHERE campaign_id = :c LIMIT 1""", c=created["campaign_id"])

    assert send["content_asset_id"] is not None, "the send must cite its asset"
    assert not send["subject"].lower().startswith("subject:")

    body = send["body_text"]
    # Exactly one greeting, supplied by the sender — the asset's own salutation
    # must have been stripped. (This visitor has no name, so it reads "Hi,".)
    assert len(re.findall(r"(?im)^\s*(hi|hello|hey|dear)\b", body)) == 1
    # The website's own words made it into the message.
    assert "warehouse automation" in body.lower()
    # And an unsubscribe link, without exception.
    assert "/unsubscribe/" in body


def test_campaign_falls_back_to_templates_without_generated_content(site) -> None:
    """A campaign must be runnable before any content has been generated."""
    from api.services import campaigns

    db.execute(
        """INSERT INTO visitors (site_id, visitor_uid, email, email_consent, consent_at)
           VALUES (:s, 'early', 'early@x.com', TRUE, now())""", s=site["id"])

    created = campaigns.create_campaign(site["id"], "Early", "trigger")
    send = db.fetch_one(
        """SELECT subject, body_text, content_asset_id FROM campaign_sends
           WHERE campaign_id = :c LIMIT 1""", c=created["campaign_id"])

    assert send["content_asset_id"] is None
    assert send["subject"]
    assert send["body_text"]


def test_call_to_action_is_not_repeated(site) -> None:
    """The generated caption usually ends with the CTA; appending it again
    produced the same sentence twice in a row."""
    from api.services import campaigns

    db.execute(
        """INSERT INTO visitors (site_id, visitor_uid, email, email_consent, consent_at)
           VALUES (:s, 'cta', 'cta@x.com', TRUE, now())""", s=site["id"])

    _cache_crawl(site["id"])
    svc.generate_for_site(site["id"], platforms=["email"])
    asset = svc.best_asset(site["id"], "email")

    created = campaigns.create_campaign(site["id"], "CTA", "trigger")
    body = db.fetch_one(
        """SELECT body_text FROM campaign_sends WHERE campaign_id = :c LIMIT 1""",
        c=created["campaign_id"])["body_text"]

    cta = (asset.get("cta") or "").strip()
    if cta:
        assert body.count(cta) <= 1, "the call to action appears twice"


def test_every_asset_carries_the_four_fields_the_generator_produces(site) -> None:
    """Module 4's output per platform is caption + hashtags + CTA + a brief.

    Storing only the first two would silently drop half of what the module
    produces, and the CTA and the brief are the parts someone has to act on.
    """
    _cache_crawl(site["id"])
    svc.generate_for_site(site["id"])

    assets = svc.list_assets(site["id"])["assets"]
    assert assets, "generation produced nothing"

    for asset in assets:
        assert asset["caption"].strip(), f"{asset['platform']} has no caption"
        assert (asset["cta"] or "").strip(), f"{asset['platform']} has no CTA"
        assert (asset["image_prompt"] or "").strip(), (
            f"{asset['platform']} has no creative brief")
        assert asset["visual_kind"] in {"image", "video"}


def test_a_video_platform_is_not_given_an_image_brief(site) -> None:
    """Regression for defect 6.

    `shorts` declares `visual: video` but had no `visual_options`, so the
    selector fell through to the default and returned an image brief. Both
    briefs share one column, so without `visual_kind` the dashboard could not
    tell that the video platform had been handed the wrong medium.
    """
    _cache_crawl(site["id"])
    svc.generate_for_site(site["id"], platforms=["shorts", "linkedin"])

    by_platform = {a["platform"]: a for a in svc.list_assets(site["id"])["assets"]}

    assert by_platform["shorts"]["visual_kind"] == "video"
    assert by_platform["linkedin"]["visual_kind"] == "image"


# ── Platform tone register ───────────────────────────────────────────────────
# The tone classifier predicts one tone for the business. It has no platform
# input and its training corpus has no platform column, so a per-platform tone
# cannot come from the model. What varies per platform is the register the brand
# voice is spoken in. These tests pin that split.

def test_brand_voice_is_constant_across_platforms(site) -> None:
    """One campaign has one brand voice.

    The register shifts per channel, but the voice the classifier measured from
    the business's own site must not. If this fails, each platform is being
    given a different brand, which is the thing brand consistency forbids.
    """
    _cache_crawl(site["id"])
    result = svc.generate_for_site(site["id"])

    brand_tones = {a["brand_tone"] for a in result["assets"]}
    assert len(brand_tones) == 1, f"brand voice split across platforms: {brand_tones}"
    assert brand_tones == {result["brand_tone"]}


def test_linkedin_and_instagram_do_not_share_an_opening_line() -> None:
    """Regression: the fast engine keyed its hook on the brand tone alone.

    Every platform therefore opened with a byte-identical sentence — LinkedIn
    and Instagram included — and only the surrounding body differed. That is
    format adaptation dressed up as voice adaptation.
    """
    from modules.m4_content import content_service as cs

    summary = {
        "product_name": "Acme", "target_audience": "founders",
        "customer_segment": "SMB", "campaign_goal": "conversion",
        "tone": "professional", "summary": "Acme automates invoicing.",
    }
    captions = {
        platform: cs._template_asset(platform, summary, ["Acme"], 0)["caption"]
        for platform in ("linkedin", "instagram")
    }
    # LinkedIn puts the hook on its own line; Instagram runs it into the body.
    # Comparing whole first lines would pass even under the old behaviour, so
    # the check is that Instagram does not *open with* LinkedIn's hook.
    linkedin_hook = captions["linkedin"].splitlines()[0]
    assert not captions["instagram"].startswith(linkedin_hook), (
        f"both platforms open with: {linkedin_hook!r}")


def test_platform_register_adapts_the_brand_voice_without_discarding_it() -> None:
    """A luxury brand stays luxury where the register allows it.

    The point of adapting rather than replacing: TikTok cannot carry luxury
    restraint, so it shifts — but LinkedIn and email can, so they must not.
    Replacing the tone outright would throw away the only tone signal that was
    actually measured.
    """
    from modules.m4_content import config as m4_config

    assert m4_config.platform_tone("linkedin", "luxury") == "luxury"
    assert m4_config.platform_tone("email", "luxury") == "luxury"
    assert m4_config.platform_tone("tiktok", "luxury") != "luxury"

    # A professional brand relaxes on the visual/short-form channels.
    assert m4_config.platform_tone("linkedin", "professional") == "professional"
    assert m4_config.platform_tone("instagram", "professional") == "friendly"


def test_unknown_platform_or_tone_falls_back_to_the_brand_voice() -> None:
    """The register map is a heuristic, so it must never invent a tone.

    An unmapped platform or an unseen classifier label returns the brand voice
    unchanged rather than guessing at a register for it.
    """
    from modules.m4_content import config as m4_config

    assert m4_config.platform_tone("mastodon", "luxury") == "luxury"
    assert m4_config.platform_tone("tiktok", "sarcastic") == "sarcastic"
    assert m4_config.platform_tone("tiktok", "") == ""


def test_stored_asset_records_the_tone_it_was_written_in(site) -> None:
    """`tone` on a stored asset is the platform tone, not the campaign tone.

    The column is per-asset, so storing the campaign-wide value in it made every
    row claim a voice the caption was not necessarily written in.
    """
    _cache_crawl(site["id"])
    svc.generate_for_site(site["id"])

    assets = svc.list_assets(site["id"])["assets"]
    assert assets

    from modules.m4_content import config as m4_config

    for asset in assets:
        assert (asset["tone"] or "").strip(), f"{asset['platform']} stored no tone"
        assert asset["tone"] == m4_config.platform_tone(
            asset["platform"], asset["brand_tone"]
        ), f"{asset['platform']} stored a tone its register does not produce"


def test_both_engines_adapt_the_tone_the_same_way() -> None:
    """The Phi-3 prompt and the fast template must not drift apart.

    They previously encoded platform voice in two unrelated places: the fast
    engine in `_HOOK_BY_TONE`, the slow one in free-text `guidance`. Both now
    resolve through the same rule, so the prompt names the adapted tone.
    """
    from modules.m4_content import config as m4_config
    from modules.m4_content import generator

    summary = {
        "product_name": "Acme", "target_audience": "founders",
        "customer_segment": "SMB", "campaign_goal": "conversion",
        "tone": "professional", "summary": "Acme automates invoicing.",
        "website_url": "https://acme.example",
    }
    prompt = generator.build_prompt(summary, "instagram")
    adapted = m4_config.platform_tone("instagram", "professional")

    assert adapted == "friendly"
    assert f"in a {adapted} tone" in prompt
    assert "Brand Voice:\nprofessional" in prompt


# ── Every channel is written for, not just defaulted ─────────────────────────
# `facebook` and `shorts` were offered by the API while having no entry in any
# of Module 4's per-platform tables, so they fell through to the generic
# defaults and rendered as the blandest cards on the dashboard. These tests
# make adding a channel without writing its rules a failure rather than a
# silent degradation.

def test_every_offered_platform_has_its_own_rules() -> None:
    from modules.m4_content import config as m4_config

    for platform in m4_config.SERVICE_PLATFORMS:
        assert platform in m4_config.PLATFORM_SPECS, (
            f"{platform} is offered but has no spec — it would fall back to "
            "DEFAULT_PLATFORM_SPEC")
        assert platform in m4_config.PLATFORM_TONE_REGISTER, (
            f"{platform} is offered but has no tone register")
        assert m4_config.register_note(platform), (
            f"{platform} is offered but has no register note for the prompt")
        assert platform in m4_config.PLATFORM_VISUAL_BRIEF, (
            f"{platform} is offered but has no creative brief")


def test_the_api_and_module_4_agree_on_which_platforms_exist() -> None:
    """One list, one place. These were declared twice and had drifted."""
    from modules.m4_content import config as m4_config

    assert svc.SUPPORTED_PLATFORMS == list(m4_config.SERVICE_PLATFORMS)


def test_each_platform_gets_its_own_copy_and_creative_brief(site) -> None:
    """Regression: the fast engine emitted one caption shape and one creative
    brief for every channel, so the dashboard showed five cards carrying the
    same sentence and the same image brief.
    """
    _cache_crawl(site["id"])
    result = svc.generate_for_site(site["id"])

    assets = result["assets"]
    assert len(assets) == len(svc.SUPPORTED_PLATFORMS)

    captions = {a["caption"] for a in assets}
    assert len(captions) == len(assets), "two platforms share a caption"

    briefs = {(a.get("image_prompt") or a.get("shorts_prompt")) for a in assets}
    assert len(briefs) == len(assets), "two platforms share a creative brief"

    ctas = {a["cta"] for a in assets}
    assert len(ctas) > 1, "the call to action is identical on every platform"


def test_a_creative_brief_names_its_own_placement(site) -> None:
    """The brief is only useful if it is cut to the placement it is for."""
    _cache_crawl(site["id"])
    svc.generate_for_site(site["id"], platforms=["instagram", "linkedin", "email"])

    by_platform = {a["platform"]: a for a in svc.list_assets(site["id"])["assets"]}

    assert "4:5" in by_platform["instagram"]["image_prompt"]
    assert "1.91:1" in by_platform["linkedin"]["image_prompt"]
    assert "banner" in by_platform["email"]["image_prompt"].lower()
