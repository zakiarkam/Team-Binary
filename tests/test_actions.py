"""The Action Plan — the advisory contract.

The product's central claim is: *we tell you what to do and write the content;
you execute it in your own tools, and it stays measurable.* These tests pin
down the three things that claim depends on.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from api import db  # noqa: E402
from api.main import app  # noqa: E402
from api.services import actions as svc  # noqa: E402

try:
    db.ping()
    DB_UP = True
except Exception:
    DB_UP = False

pytestmark = pytest.mark.skipif(not DB_UP, reason="PostgreSQL is not running")


@pytest.fixture(scope="module")
def client() -> TestClient:
    db.init_schema()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def site(client: TestClient):
    res = client.post("/sites", json={"name": "Action Test",
                                      "url": "https://actions.example"})
    body = res.json()["site"]
    yield body
    db.execute("DELETE FROM sites WHERE id = :i", i=body["id"])


def _contactable(site_id: int, uid: str, segment: str = "High Intent") -> int:
    row = db.fetch_one(
        """
        INSERT INTO visitors (site_id, visitor_uid, email, name,
                              email_consent, consent_at)
        VALUES (:s, :u, :e, 'Test Person', TRUE, now())
        RETURNING id
        """,
        s=site_id, u=uid, e=f"{uid}@example.com",
    )
    vid = int(row["id"])
    db.execute(
        """INSERT INTO user_segments (site_id, visitor_id, segment_name,
                                      segment_method, segment_confidence)
           VALUES (:s, :v, :n, 'hybrid', 0.8)""",
        s=site_id, v=vid, n=segment)
    return vid


def _asset(site_id: int, platform: str) -> int:
    row = db.fetch_one(
        """
        INSERT INTO content_assets (site_id, platform, caption, hashtags, cta,
                                    image_prompt, final_score)
        VALUES (:s, :p, 'A caption about the product', '["#one","#two"]'::jsonb,
                'Start free', 'A bright desk scene', 0.8)
        RETURNING id
        """,
        s=site_id, p=platform)
    return int(row["id"])


# ── The plan is advice, not delivery ─────────────────────────────────────────

def test_a_plan_produces_ready_to_use_content_for_email_and_posts(site) -> None:
    _contactable(site["id"], "act-v1")
    for platform in ("instagram", "linkedin"):
        _asset(site["id"], platform)

    built = svc.build_plan(site["id"], "hybrid")
    assert built["email_actions"] >= 1
    assert built["post_actions"] >= 2

    plan = svc.current_plan(site["id"])
    kinds = {a["kind"] for a in plan["actions"]}
    assert kinds == {"email", "post"}

    email = next(a for a in plan["actions"] if a["kind"] == "email")
    assert email["subject"] and email["body"], "an email action must be writable as-is"
    assert email["audience_size"] >= 1
    assert email["rationale"], "every action must say why it is being suggested"

    post = next(a for a in plan["actions"] if a["kind"] == "post")
    assert post["caption"] and post["hashtags"]
    assert post["rationale"]


def test_nothing_is_sent_while_a_plan_is_built(site) -> None:
    """Building a plan must never contact a recipient.

    The guard is structural: no interaction row exists until the company says
    it executed the action.
    """
    _contactable(site["id"], "act-v2")
    _asset(site["id"], "instagram")
    svc.build_plan(site["id"], "hybrid")

    interactions = db.fetch_one(
        "SELECT count(*) AS n FROM interactions WHERE site_id = :s", s=site["id"])
    assert interactions["n"] == 0

    statuses = db.fetch_all(
        """SELECT DISTINCT cs.status FROM campaign_sends cs
           JOIN campaigns c ON c.id = cs.campaign_id WHERE c.site_id = :s""",
        s=site["id"])
    assert {r["status"] for r in statuses} == {"scheduled"}, \
        "drafts stay planned; nothing is marked sent"


# ── The measurement trick: a post we never published is still tracked ────────

def test_a_hand_published_post_stays_measurable(site, client: TestClient) -> None:
    """The link inside the content is ours, whoever publishes the post.

    Clicking it records the click and forwards the visitor with a UTM tag, so
    the existing attribution model sees the platform that sent them.
    """
    _contactable(site["id"], "act-v3")
    _asset(site["id"], "instagram")
    svc.build_plan(site["id"], "hybrid")

    plan = svc.current_plan(site["id"])
    post = next(a for a in plan["actions"] if a["kind"] == "post")
    token = post["tracked_link"].rsplit("/", 1)[-1]

    res = client.get(f"/l/{token}", follow_redirects=False)
    assert res.status_code == 302
    target = res.headers["location"]
    assert "utm_source=" in target and "utm_medium=social" in target, \
        "the redirect must tag the visit with its platform"

    row = db.fetch_one(
        "SELECT outcome FROM content_actions WHERE track_token = :t", t=token)
    assert row["outcome"].get("clicks") == 1


def test_an_unknown_short_link_redirects_rather_than_erroring(
        client: TestClient) -> None:
    """A public marketing link that 404s is worse than an untracked one."""
    res = client.get("/l/not-a-real-token", follow_redirects=False)
    assert res.status_code == 302


# ── Executing an action is self-reported, and labelled as such ───────────────

def test_marking_an_email_done_records_it_as_self_reported(site) -> None:
    _contactable(site["id"], "act-v4")
    built = svc.build_plan(site["id"], "hybrid")

    step = db.fetch_one(
        "SELECT min(step) AS s FROM campaign_sends WHERE campaign_id = :c",
        c=built["plan_id"])["s"]
    result = svc.mark_email_executed(built["plan_id"], step)
    assert result["messages"] >= 1

    row = db.fetch_one(
        """SELECT event_type, meta, source FROM interactions
           WHERE campaign_id = :c LIMIT 1""", c=built["plan_id"])
    assert row["event_type"] == "sent"
    assert row["meta"].get("self_reported") is True, \
        "the platform did not watch it leave; the funnel must say so"
    # Live visitor → live row. The `source` derivation is unchanged.
    assert row["source"] == "live"


def test_marking_a_post_done_takes_it_off_the_list(site) -> None:
    _contactable(site["id"], "act-v5")
    _asset(site["id"], "instagram")
    svc.build_plan(site["id"], "hybrid")

    before = svc.current_plan(site["id"])
    post = next(a for a in before["actions"] if a["kind"] == "post")
    svc.mark_post_executed(post["id"])

    after = svc.current_plan(site["id"])
    assert post["id"] not in [a.get("id") for a in after["actions"]
                              if a["kind"] == "post"]
    # ...but it is still there in the history.
    with_done = svc.current_plan(site["id"], include_done=True)
    done = next(a for a in with_done["actions"]
                if a["kind"] == "post" and a["id"] == post["id"])
    assert done["status"] == "executed" and done["executed_at"] is not None


def test_dataset_visitors_never_produce_a_live_self_reported_send(site) -> None:
    """The honesty invariant holds on this path too."""
    row = db.fetch_one(
        """INSERT INTO visitors (site_id, visitor_uid, email, email_consent,
                                 consent_at, source)
           VALUES (:s, 'act-ds', 'ds@example.invalid', TRUE, now(), 'dataset')
           RETURNING id""", s=site["id"])
    db.execute(
        """INSERT INTO user_segments (site_id, visitor_id, segment_name,
                                      segment_method, segment_confidence)
           VALUES (:s, :v, 'High Intent', 'hybrid', 0.8)""",
        s=site["id"], v=row["id"])

    built = svc.build_plan(site["id"], "hybrid")
    step = db.fetch_one(
        "SELECT min(step) AS s FROM campaign_sends WHERE campaign_id = :c",
        c=built["plan_id"])["s"]
    svc.mark_email_executed(built["plan_id"], step)

    leaked = db.fetch_one(
        """SELECT count(*) AS n FROM interactions i
           JOIN visitors v ON v.id = i.visitor_id
           WHERE i.site_id = :s AND i.source = 'live'
             AND v.source = 'dataset'""",
        s=site["id"])
    assert leaked["n"] == 0


# ── API surface ──────────────────────────────────────────────────────────────

def test_plan_endpoints_round_trip(site, client: TestClient) -> None:
    _contactable(site["id"], "act-v6")
    _asset(site["id"], "linkedin")

    created = client.post(f"/sites/{site['id']}/plan", json={"strategy": "trigger"})
    assert created.status_code == 201
    assert created.json()["post_actions"] >= 1

    plan = client.get(f"/sites/{site['id']}/plan")
    assert plan.status_code == 200
    assert plan.json()["counts"]["total"] >= 2
    assert "advises" in plan.json()["how_to_use"]


def test_unknown_strategy_is_rejected(site, client: TestClient) -> None:
    res = client.post(f"/sites/{site['id']}/plan", json={"strategy": "wishful"})
    assert res.status_code == 422
