"""Phase 3 tests — campaign automation, email delivery, and tracking.

The consent and safety rules are tested first and hardest, because every other
defect in this system costs a wrong number in a report, while a defect here
costs mailing a real person who never agreed to it.

Requires PostgreSQL:  docker-compose up -d
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api import db
from api.main import app
from api.services import campaigns as svc
from api.services import email_sender

pytestmark = pytest.mark.skipif(
    not db.ping(), reason="PostgreSQL is not reachable — run `docker-compose up -d`"
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    db.init_schema()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def site(client: TestClient):
    res = client.post("/sites", json={"name": "Campaign Test",
                                      "url": "https://campaign.example"})
    body = res.json()["site"]
    yield body
    db.execute("DELETE FROM sites WHERE id = :i", i=body["id"])


def _visitor(site_id: int, uid: str, email: str | None = None,
             consent: bool = False, segment: str | None = None) -> int:
    row = db.fetch_one(
        """
        INSERT INTO visitors (site_id, visitor_uid, email, name, email_consent,
                              consent_at)
        VALUES (:s, :u, :e, 'Test Person', :c,
                CASE WHEN :c THEN now() ELSE NULL END)
        RETURNING id
        """,
        s=site_id, u=uid, e=email, c=consent,
    )
    vid = int(row["id"])
    if segment:
        db.execute(
            """INSERT INTO user_segments (site_id, visitor_id, segment_name,
                                          segment_method, segment_confidence)
               VALUES (:s, :v, :n, 'hybrid', 0.8)""",
            s=site_id, v=vid, n=segment)
    return vid


# ── Consent ──────────────────────────────────────────────────────────────────

def test_only_consented_visitors_are_emailable(site) -> None:
    _visitor(site["id"], "anon", None, False)                    # anonymous
    _visitor(site["id"], "known", "known@x.com", False)          # no consent
    ok = _visitor(site["id"], "ok", "ok@x.com", True)            # consented

    recipients = email_sender.eligible_recipients(site["id"])
    assert [r["visitor_id"] for r in recipients] == [ok]


def test_unsubscribed_visitors_are_never_re_emailed(site) -> None:
    vid = _visitor(site["id"], "gone", "gone@x.com", True)
    db.execute(
        """UPDATE visitors SET email_consent = FALSE, unsubscribed_at = now()
           WHERE id = :i""", i=vid)

    assert email_sender.eligible_recipients(site["id"]) == []


def test_every_message_carries_an_unsubscribe_link(site) -> None:
    composed = email_sender.compose("Subject", "Body copy", "tok-123", "Alex")
    assert "/unsubscribe/tok-123" in composed["html"]
    assert "/unsubscribe/tok-123" in composed["text"], "plain-text part needs it too"


def test_consent_is_rechecked_at_send_time(site, client: TestClient) -> None:
    """Someone may unsubscribe between being scheduled and being sent to."""
    vid = _visitor(site["id"], "late", "late@x.com", True)
    created = svc.create_campaign(site["id"], "Late", "fixed")
    assert created["recipients"] == 1

    db.execute("""UPDATE visitors SET email_consent = FALSE,
                         unsubscribed_at = now() WHERE id = :i""", i=vid)

    result = email_sender.deliver_due_sends(created["campaign_id"], force=True)
    assert result["sent"] == 0
    assert result["skipped"] >= 1


# ── Tracking safety ──────────────────────────────────────────────────────────

def test_click_redirect_cannot_be_pointed_anywhere(site, client: TestClient) -> None:
    """Targets are resolved by index from the stored list, so there is no way to
    turn this endpoint into an open redirect."""
    _visitor(site["id"], "clicker", "click@x.com", True)
    created = svc.create_campaign(site["id"], "Redirect", "hybrid")
    email_sender.deliver_due_sends(created["campaign_id"], force=True)

    send = db.fetch_one(
        "SELECT track_token, links FROM campaign_sends WHERE campaign_id=:c LIMIT 1",
        c=created["campaign_id"])
    token = send["track_token"]

    # A valid index redirects to a link that was in the message.
    ok = client.get(f"/track/click/{token}/0", follow_redirects=False)
    assert ok.status_code == 302
    assert ok.headers["location"] in send["links"]

    # Out-of-range and negative indices are refused, not clamped.
    assert client.get(f"/track/click/{token}/99", follow_redirects=False).status_code == 404
    # An unknown token cannot resolve to anything at all.
    assert client.get("/track/click/nope/0", follow_redirects=False).status_code == 404


def test_open_pixel_always_returns_an_image(client: TestClient) -> None:
    """Even for an unknown token: a broken image in someone's inbox is a poor
    way to report an error."""
    res = client.get("/track/open/unknown-token.gif")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/gif"
    assert res.content[:3] == b"GIF"


def test_repeat_opens_are_not_double_counted(site, client: TestClient) -> None:
    """Mail clients re-fetch the pixel on preview and re-open; counting those
    separately would inflate the open rate."""
    _visitor(site["id"], "opener", "open@x.com", True)
    created = svc.create_campaign(site["id"], "Opens", "hybrid")
    email_sender.deliver_due_sends(created["campaign_id"], force=True)

    token = db.fetch_one(
        "SELECT track_token FROM campaign_sends WHERE campaign_id=:c LIMIT 1",
        c=created["campaign_id"])["track_token"]

    for _ in range(4):
        client.get(f"/track/open/{token}.gif")

    n = db.fetch_one(
        """SELECT count(*) c FROM interactions
           WHERE campaign_id = :c AND event_type = 'open'""",
        c=created["campaign_id"])["c"]
    assert n == 1


def test_unsubscribe_revokes_consent_and_cancels_queued_mail(
    site, client: TestClient
) -> None:
    vid = _visitor(site["id"], "quitter", "quit@x.com", True)
    created = svc.create_campaign(site["id"], "Quit", "fixed")   # 5 steps queued
    email_sender.deliver_due_sends(created["campaign_id"], force=True, limit=1)

    token = db.fetch_one(
        """SELECT track_token FROM campaign_sends
           WHERE campaign_id=:c AND status <> 'scheduled' LIMIT 1""",
        c=created["campaign_id"])["track_token"]

    assert client.get(f"/unsubscribe/{token}").status_code == 200

    visitor = db.fetch_one(
        "SELECT email_consent, unsubscribed_at FROM visitors WHERE id=:i", i=vid)
    assert visitor["email_consent"] is False
    assert visitor["unsubscribed_at"] is not None

    still_queued = db.fetch_one(
        """SELECT count(*) c FROM campaign_sends
           WHERE visitor_id = :v AND status = 'scheduled'""", v=vid)["c"]
    assert still_queued == 0, "queued mail must be cancelled immediately"


# ── Strategies ───────────────────────────────────────────────────────────────

def test_fixed_schedules_the_whole_sequence_upfront(site) -> None:
    _visitor(site["id"], "f1", "f1@x.com", True)
    created = svc.create_campaign(site["id"], "Fixed", "fixed")

    n = db.fetch_one("SELECT count(*) c FROM campaign_sends WHERE campaign_id=:c",
                     c=created["campaign_id"])["c"]
    assert n == len(svc.STEPS)


def test_trigger_and_hybrid_only_schedule_the_opener(site) -> None:
    _visitor(site["id"], "t1", "t1@x.com", True)
    for strategy in ("trigger", "hybrid"):
        created = svc.create_campaign(site["id"], strategy, strategy)
        n = db.fetch_one("SELECT count(*) c FROM campaign_sends WHERE campaign_id=:c",
                         c=created["campaign_id"])["c"]
        assert n == 1, f"{strategy} must wait for behaviour before queueing more"


def test_hybrid_personalises_the_opener_by_segment(site) -> None:
    _visitor(site["id"], "h1", "h1@x.com", True, segment="High Intent")
    _visitor(site["id"], "h2", "h2@x.com", True, segment="Price Sensitive")

    created = svc.create_campaign(site["id"], "Hybrid", "hybrid")
    subjects = {r["subject"] for r in db.fetch_all(
        "SELECT subject FROM campaign_sends WHERE campaign_id=:c",
        c=created["campaign_id"])}
    assert len(subjects) == 2, "each segment should get its own opening message"


def test_operational_complexity_is_recorded_per_strategy() -> None:
    """The research compares policies on complexity as well as outcome, so a
    hybrid policy that wins narrowly can still be judged against its cost."""
    assert svc.POLICY_RULE_COUNT["fixed"] < svc.POLICY_RULE_COUNT["trigger"]
    assert svc.POLICY_RULE_COUNT["trigger"] < svc.POLICY_RULE_COUNT["hybrid"]


def test_unknown_strategy_is_rejected(site) -> None:
    with pytest.raises(ValueError, match="strategy"):
        svc.create_campaign(site["id"], "Bad", "telepathy")


# ── Delivery + funnel ────────────────────────────────────────────────────────

def test_dry_run_records_the_funnel_without_sending(site) -> None:
    """With SMTP unconfigured everything is composed and recorded but nothing
    leaves the machine — the demo path."""
    _visitor(site["id"], "d1", "d1@x.com", True)
    created = svc.create_campaign(site["id"], "Dry", "hybrid")

    result = email_sender.deliver_due_sends(created["campaign_id"], force=True)
    assert result["dry_run"] is True
    assert result["sent"] == 1

    row = db.fetch_one(
        """SELECT status, sent_at FROM campaign_sends WHERE campaign_id=:c""",
        c=created["campaign_id"])
    assert row["status"] == "dry_run"
    assert row["sent_at"] is not None

    sent_events = db.fetch_one(
        """SELECT count(*) c FROM interactions
           WHERE campaign_id=:c AND event_type='sent'""",
        c=created["campaign_id"])
    assert sent_events["c"] == 1


def test_metrics_do_not_multiply_sends_by_interactions(site) -> None:
    """Regression: joining campaign_sends to interactions on campaign_id alone
    produced a cartesian product — 16 sends became 256."""
    for i in range(4):
        _visitor(site["id"], f"m{i}", f"m{i}@x.com", True)

    created = svc.create_campaign(site["id"], "Metrics", "hybrid")
    email_sender.deliver_due_sends(created["campaign_id"], force=True)

    metrics = svc.campaign_metrics(created["campaign_id"])
    assert metrics["recipients"] == 4
    assert metrics["sent"] == 4
    assert metrics["open_rate"] == 0.0


# ── Conversion attribution ───────────────────────────────────────────────────

def _collect(client: TestClient, site_key: str, uid: str, events: list[dict]):
    return client.post("/collect", content=json.dumps({
        "site_key": site_key, "visitor_uid": uid, "session_id": "s1",
        "context": {"path": "/pricing", "device": "desktop"},
        "events": [{"type": e["type"], "path": "/pricing",
                    "props": e.get("props", {}),
                    "ts": datetime.now(timezone.utc).isoformat()} for e in events],
    }), headers={"Content-Type": "text/plain"})


def test_purchase_after_a_click_is_credited_to_the_campaign(
    site, client: TestClient
) -> None:
    _visitor(site["id"], "buyer", "buyer@x.com", True)
    created = svc.create_campaign(site["id"], "Attrib", "hybrid")
    email_sender.deliver_due_sends(created["campaign_id"], force=True)

    token = db.fetch_one(
        "SELECT track_token FROM campaign_sends WHERE campaign_id=:c LIMIT 1",
        c=created["campaign_id"])["track_token"]
    client.get(f"/track/click/{token}/0", follow_redirects=False)

    _collect(client, site["site_key"], "buyer",
             [{"type": "purchase", "props": {"plan": "growth", "value": 49}}])

    conv = db.fetch_one(
        """SELECT count(*) c, max(meta->>'attribution') a FROM interactions
           WHERE campaign_id=:c AND event_type='convert'""",
        c=created["campaign_id"])
    assert conv["c"] == 1
    assert conv["a"] == "last_touch"


def test_purchase_without_a_click_is_not_claimed(site, client: TestClient) -> None:
    """An organic purchase is real, but it is not the campaign's to take credit
    for — inflating conversions here would corrupt every downstream metric."""
    _visitor(site["id"], "organic", "organic@x.com", True)
    created = svc.create_campaign(site["id"], "Organic", "hybrid")
    email_sender.deliver_due_sends(created["campaign_id"], force=True)

    _collect(client, site["site_key"], "organic",
             [{"type": "purchase", "props": {"plan": "starter"}}])

    conv = db.fetch_one(
        """SELECT count(*) c FROM interactions
           WHERE campaign_id=:c AND event_type='convert'""",
        c=created["campaign_id"])["c"]
    assert conv == 0


def test_a_single_send_is_credited_at_most_one_conversion(
    site, client: TestClient
) -> None:
    _visitor(site["id"], "repeat", "repeat@x.com", True)
    created = svc.create_campaign(site["id"], "Repeat", "hybrid")
    email_sender.deliver_due_sends(created["campaign_id"], force=True)

    token = db.fetch_one(
        "SELECT track_token FROM campaign_sends WHERE campaign_id=:c LIMIT 1",
        c=created["campaign_id"])["track_token"]
    client.get(f"/track/click/{token}/0", follow_redirects=False)

    for _ in range(3):
        _collect(client, site["site_key"], "repeat",
                 [{"type": "purchase", "props": {"plan": "growth"}}])

    conv = db.fetch_one(
        """SELECT count(*) c FROM interactions
           WHERE campaign_id=:c AND event_type='convert'""",
        c=created["campaign_id"])["c"]
    assert conv == 1


# ── Reachable-audience endpoint ──────────────────────────────────────────────

def test_dataset_visitors_never_produce_live_funnel_events(
    site, client: TestClient
) -> None:
    """The honesty invariant for the whole project.

    Imported research users go through the same write paths as a live browser,
    so `source` cannot be asserted by the caller — it is derived from the
    visitor the event belongs to. Without this, replaying a dataset would
    silently manufacture results that look observed.
    """
    real_id = _visitor(site["id"], "genuine", "genuine@x.com", True)
    fake_id = _visitor(site["id"], "from-dataset", "ds@example.invalid", True)
    db.execute("UPDATE visitors SET source = 'dataset' WHERE id = :i", i=fake_id)

    created = svc.create_campaign(site["id"], "Mixed", "hybrid")
    email_sender.deliver_due_sends(created["campaign_id"], force=True)

    for token_row in db.fetch_all(
        "SELECT track_token FROM campaign_sends WHERE campaign_id=:c",
        c=created["campaign_id"],
    ):
        client.get(f"/track/open/{token_row['track_token']}.gif")

    flags = {
        r["visitor_id"]: r["source"]
        for r in db.fetch_all(
            "SELECT DISTINCT visitor_id, source FROM interactions WHERE campaign_id=:c",
            c=created["campaign_id"])
    }
    assert flags[real_id] == "live"
    assert flags[fake_id] == "dataset"

    leaked = db.fetch_one(
        """SELECT count(*) n FROM interactions i
           JOIN visitors v ON v.id = i.visitor_id
           WHERE i.source = 'live' AND v.source = 'dataset'""")["n"]
    assert leaked == 0

    metrics = svc.campaign_metrics(created["campaign_id"])
    assert metrics["data_basis"] == "mixed", "reports must say what they rest on"


def test_reachable_endpoint_explains_the_shortfall(site, client: TestClient) -> None:
    _visitor(site["id"], "a1", None, False)
    _visitor(site["id"], "a2", "a2@x.com", False)
    _visitor(site["id"], "a3", "a3@x.com", True)

    body = client.get(f"/sites/{site['id']}/audience/reachable").json()
    assert body["visitors"] == 3
    assert body["anonymous"] == 1
    assert body["known_no_consent"] == 1
    assert body["reachable"] == 1


# ── The production scheduler tick ────────────────────────────────────────────

def test_scheduler_ticks_every_running_campaign(site, client: TestClient) -> None:
    """One POST refreshes the Action Plan for every running plan.

    This is what a cron job calls in production. It must add recommendations
    and never send anything: an unattended job that mails people on a timer is
    precisely what an advisory platform must not become.
    """
    _visitor(site["id"], "sched-v1", "sched1@example.com", consent=True,
             segment="High Intent")
    created = client.post(f"/sites/{site['id']}/campaigns",
                          json={"name": "Sched", "strategy": "trigger"}).json()
    cid = created["campaign_id"]
    # Sending marks it running; the scheduler should then pick it up.
    client.post(f"/campaigns/{cid}/send?force=true")

    res = client.post("/campaigns/scheduler/run")
    assert res.status_code == 200
    body = res.json()
    assert body["plans_ticked"] >= 1
    ours = [r for r in body["results"] if r["campaign_id"] == cid]
    assert ours and "error" not in ours[0]
    # The tick queues recommendations; it must never deliver anything itself.
    assert "new_actions" in ours[0]
    assert "sent" not in ours[0]


def test_scheduler_requires_the_token_when_one_is_configured(
        client: TestClient, monkeypatch) -> None:
    from api.settings import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "scheduler_token", "s3cret")
    try:
        assert client.post("/campaigns/scheduler/run").status_code == 401
        assert client.post(
            "/campaigns/scheduler/run",
            headers={"X-Scheduler-Token": "wrong"},
        ).status_code == 401
        assert client.post(
            "/campaigns/scheduler/run",
            headers={"X-Scheduler-Token": "s3cret"},
        ).status_code == 200
    finally:
        monkeypatch.setattr(settings, "scheduler_token", "")
