"""Phase 1 tests — visitor tracking, event ingestion, and consent.

These cover the rules the rest of the system depends on:
  · a batch of events becomes one visitor plus N event rows
  · acquisition attribution (utm_*) is captured once, on first sight
  · an email only ever becomes contactable with explicit consent
  · behavioural features come back as numbers, not strings

Requires PostgreSQL:  docker-compose up -d
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api import db
from api.main import app

pytestmark = pytest.mark.skipif(
    not db.ping(), reason="PostgreSQL is not reachable — run `docker-compose up -d`"
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    db.init_schema()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def site(client: TestClient) -> dict:
    """A throwaway site, removed (with all its data) after each test."""
    res = client.post("/sites", json={"name": "Test Co", "url": "https://test.example"})
    assert res.status_code == 201
    body = res.json()
    yield body["site"]
    db.execute("DELETE FROM sites WHERE id = :i", i=body["site"]["id"])


def _batch(site_key: str, uid: str, events: list[dict], **ctx) -> dict:
    context = {"path": "/", "referrer": None, "device": "desktop", **ctx}
    return {
        "site_key": site_key,
        "visitor_uid": uid,
        "session_id": "sess-1",
        "context": context,
        "events": [
            {"type": e["type"], "path": e.get("path", "/"),
             "props": e.get("props", {}),
             "ts": datetime.now(timezone.utc).isoformat()}
            for e in events
        ],
    }


def _post(client: TestClient, payload: dict):
    # text/plain matches what mos.js sends (it avoids a CORS preflight).
    return client.post("/collect", content=json.dumps(payload),
                       headers={"Content-Type": "text/plain"})


# ── Ingestion ────────────────────────────────────────────────────────────────

def test_batch_creates_one_visitor_and_all_events(client: TestClient, site: dict) -> None:
    res = _post(client, _batch(site["site_key"], "uid-a", [
        {"type": "page_view", "path": "/"},
        {"type": "scroll", "props": {"depth": 50}},
        {"type": "click", "props": {"label": "cta"}},
    ]))
    assert res.status_code == 204

    summary = client.get(f"/sites/{site['id']}/audience/summary").json()
    assert summary["totals"]["visitors"] == 1
    assert summary["totals"]["events"] == 3


def test_same_uid_is_one_visitor_across_batches(client: TestClient, site: dict) -> None:
    for _ in range(3):
        _post(client, _batch(site["site_key"], "uid-b", [{"type": "page_view"}]))

    summary = client.get(f"/sites/{site['id']}/audience/summary").json()
    assert summary["totals"]["visitors"] == 1, "repeat visits must not duplicate the visitor"
    assert summary["totals"]["events"] == 3


def test_unknown_site_key_is_rejected(client: TestClient) -> None:
    res = _post(client, _batch("mos_does_not_exist", "uid-x", [{"type": "page_view"}]))
    assert res.status_code == 404


def test_oversized_batch_is_rejected(client: TestClient, site: dict) -> None:
    res = _post(client, _batch(site["site_key"], "uid-c",
                               [{"type": "page_view"}] * 51))
    assert res.status_code == 413


def test_malformed_payload_is_rejected(client: TestClient) -> None:
    res = client.post("/collect", content="not json",
                      headers={"Content-Type": "text/plain"})
    assert res.status_code == 400


# ── Attribution ──────────────────────────────────────────────────────────────

def test_acquisition_source_is_captured_once(client: TestClient, site: dict) -> None:
    """First touch wins: a returning visit must not overwrite what brought
    the visitor in, or Module 3's attribution would credit the wrong channel."""
    _post(client, _batch(site["site_key"], "uid-d", [{"type": "page_view"}],
                         utm_source="linkedin", utm_campaign="launch"))
    _post(client, _batch(site["site_key"], "uid-d", [{"type": "page_view"}],
                         utm_source="google", utm_campaign="retarget"))

    row = db.fetch_one(
        "SELECT utm_source, utm_campaign FROM visitors WHERE visitor_uid = 'uid-d'")
    assert row["utm_source"] == "linkedin"
    assert row["utm_campaign"] == "launch"


# ── Consent ──────────────────────────────────────────────────────────────────

def test_identify_without_consent_is_known_but_not_contactable(
    client: TestClient, site: dict
) -> None:
    _post(client, _batch(site["site_key"], "uid-e", [
        {"type": "identify", "props": {"email": "no@consent.com", "consent": False}},
    ]))
    row = db.fetch_one("SELECT email, email_consent FROM visitors WHERE visitor_uid='uid-e'")
    assert row["email"] == "no@consent.com"
    assert row["email_consent"] is False, "consent must never be implied by identifying"


def test_identify_with_consent_makes_visitor_contactable(
    client: TestClient, site: dict
) -> None:
    _post(client, _batch(site["site_key"], "uid-f", [
        {"type": "identify", "props": {"email": "Yes@Consent.com", "consent": True}},
    ]))
    row = db.fetch_one(
        "SELECT email, email_consent, consent_at FROM visitors WHERE visitor_uid='uid-f'")
    assert row["email"] == "yes@consent.com", "emails are normalised to lowercase"
    assert row["email_consent"] is True
    assert row["consent_at"] is not None


def test_later_identify_cannot_silently_revoke_consent(
    client: TestClient, site: dict
) -> None:
    """A second form submit with the box unticked must not quietly opt someone
    out — only an explicit consent event or unsubscribe may do that."""
    _post(client, _batch(site["site_key"], "uid-g", [
        {"type": "identify", "props": {"email": "a@b.com", "consent": True}}]))
    _post(client, _batch(site["site_key"], "uid-g", [
        {"type": "identify", "props": {"email": "a@b.com", "consent": False}}]))

    row = db.fetch_one("SELECT email_consent FROM visitors WHERE visitor_uid='uid-g'")
    assert row["email_consent"] is True


def test_explicit_consent_withdrawal_is_honoured(client: TestClient, site: dict) -> None:
    _post(client, _batch(site["site_key"], "uid-h", [
        {"type": "identify", "props": {"email": "c@d.com", "consent": True}}]))
    _post(client, _batch(site["site_key"], "uid-h", [
        {"type": "consent", "props": {"consent": False}}]))

    row = db.fetch_one(
        "SELECT email_consent, unsubscribed_at FROM visitors WHERE visitor_uid='uid-h'")
    assert row["email_consent"] is False
    assert row["unsubscribed_at"] is not None


def test_invalid_email_is_ignored(client: TestClient, site: dict) -> None:
    _post(client, _batch(site["site_key"], "uid-i", [
        {"type": "identify", "props": {"email": "not-an-email", "consent": True}}]))
    row = db.fetch_one("SELECT email, email_consent FROM visitors WHERE visitor_uid='uid-i'")
    assert row["email"] is None
    assert row["email_consent"] is False


# ── Features consumed by Module 1 ────────────────────────────────────────────

def test_behavioural_features_are_numbers_not_strings(
    client: TestClient, site: dict
) -> None:
    _post(client, _batch(site["site_key"], "uid-j", [
        {"type": "page_view", "path": "/"},
        {"type": "page_view", "path": "/pricing"},
        {"type": "scroll", "props": {"depth": 75}},
        {"type": "click", "props": {"label": "buy"}},
        {"type": "page_exit", "props": {"seconds": 42}},
        {"type": "purchase", "props": {"plan": "growth"}},
    ]))

    v = client.get(f"/sites/{site['id']}/visitors").json()["visitors"][0]

    assert v["page_views"] == 2
    assert v["unique_pages"] == 2
    assert v["clicks"] == 1
    assert v["purchases"] == 1
    # These feed the segmentation model, so their types matter.
    assert isinstance(v["max_scroll_depth"], float) and v["max_scroll_depth"] == 75.0
    assert isinstance(v["time_on_site_seconds"], float) and v["time_on_site_seconds"] == 42.0
    assert isinstance(v["days_since_last_seen"], float)


def test_reachable_filter_returns_only_consented_visitors(
    client: TestClient, site: dict
) -> None:
    _post(client, _batch(site["site_key"], "uid-k", [
        {"type": "identify", "props": {"email": "k@x.com", "consent": True}}]))
    _post(client, _batch(site["site_key"], "uid-l", [
        {"type": "identify", "props": {"email": "l@x.com", "consent": False}}]))

    res = client.get(f"/sites/{site['id']}/visitors?reachable_only=true").json()
    assert res["total"] == 1
    assert res["visitors"][0]["email"] == "k@x.com"


# ── The snippet itself ───────────────────────────────────────────────────────

def test_snippet_is_served_and_self_configuring(client: TestClient) -> None:
    res = client.get("/mos.js")
    assert res.status_code == 200
    assert "javascript" in res.headers["content-type"]

    body = res.text
    assert "data-site" in body, "the snippet must read its own site key"
    assert "doNotTrack" in body, "Do Not Track must be honoured"
    # Cross-origin is the whole point — the snippet runs on the customer's domain.
    assert res.headers.get("Access-Control-Allow-Origin") == "*"


def test_collect_allows_cross_origin_posts(client: TestClient, site: dict) -> None:
    res = _post(client, _batch(site["site_key"], "uid-m", [{"type": "page_view"}]))
    assert res.headers.get("Access-Control-Allow-Origin") == "*"
