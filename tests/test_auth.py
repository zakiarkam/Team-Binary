"""Accounts and tenant isolation.

The product story is: a company (say, Aymex) creates an account, registers its
website, and the system markets to that website's visitors. The one property
that must hold for that story to be safe is isolation — company A must never
be able to see or touch company B's audience. These tests pin it down.
"""

from __future__ import annotations

import uuid

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from api import db  # noqa: E402
from api.main import app  # noqa: E402

try:
    db.ping()
    DB_UP = True
except Exception:
    DB_UP = False

pytestmark = pytest.mark.skipif(not DB_UP, reason="PostgreSQL is not running")


# Every account a test creates is recorded here, and the autouse fixture
# below deletes them after each test — even when the test fails BEFORE its
# own try/finally cleanup starts. (That exact gap once leaked three accounts
# into the demo database: the second _register call failed, and the first
# account had no finally to protect it yet.)
_created_user_ids: list[int] = []


@pytest.fixture(autouse=True)
def _no_leaked_accounts():
    yield
    while _created_user_ids:
        _cleanup_user(_created_user_ids.pop())


def _register(client: TestClient, company: str) -> dict:
    """Create a fresh account and return {user, token}."""
    slug = company.lower().replace(" ", "-")
    res = client.post("/auth/register", json={
        "email": f"{slug}-{uuid.uuid4().hex[:8]}@example.com",
        "password": "a-strong-password",
        "company_name": company,
    })
    assert res.status_code == 201, res.text
    body = res.json()
    _created_user_ids.append(body["user"]["id"])
    return body


def _cleanup_user(user_id: int) -> None:
    # Cascades to sessions and owned sites.
    db.execute("DELETE FROM users WHERE id = :i", i=user_id)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_register_login_me_logout_roundtrip() -> None:
    with TestClient(app) as client:
        reg = _register(client, "Aymex")
        try:
            email = reg["user"]["email"]

            # The registration token works immediately.
            me = client.get("/auth/me", headers=_auth(reg["token"]))
            assert me.status_code == 200
            assert me.json()["user"]["company_name"] == "Aymex"

            # Fresh login issues a fresh token.
            login = client.post("/auth/login", json={
                "email": email, "password": "a-strong-password"})
            assert login.status_code == 200
            token = login.json()["token"]

            # Logout kills the token instantly — the session is a DB row.
            client.post("/auth/logout", headers=_auth(token))
            assert client.get("/auth/me", headers=_auth(token)).status_code == 401
        finally:
            _cleanup_user(reg["user"]["id"])


def test_wrong_password_and_unknown_email_are_indistinguishable() -> None:
    with TestClient(app) as client:
        reg = _register(client, "Aymex")
        try:
            wrong_pw = client.post("/auth/login", json={
                "email": reg["user"]["email"], "password": "not-the-password"})
            no_user = client.post("/auth/login", json={
                "email": f"nobody-{uuid.uuid4().hex[:8]}@example.com",
                "password": "whatever-here"})
            # Same status, same message: a failed login must not confirm
            # whether the account exists.
            assert wrong_pw.status_code == no_user.status_code == 401
            assert wrong_pw.json()["detail"] == no_user.json()["detail"]
        finally:
            _cleanup_user(reg["user"]["id"])


def test_duplicate_email_is_rejected() -> None:
    with TestClient(app) as client:
        reg = _register(client, "Aymex")
        try:
            dup = client.post("/auth/register", json={
                "email": reg["user"]["email"].upper(),  # case must not bypass it
                "password": "another-password",
                "company_name": "Impostor Ltd",
            })
            assert dup.status_code == 409
        finally:
            _cleanup_user(reg["user"]["id"])


def test_a_company_only_sees_its_own_sites() -> None:
    with TestClient(app) as client:
        aymex = _register(client, "Aymex")
        rival = _register(client, "Rival Corp")
        try:
            created = client.post(
                "/sites",
                json={"name": "Aymex", "url": "https://aymex.example"},
                headers=_auth(aymex["token"]),
            )
            assert created.status_code == 201
            site_id = created.json()["site"]["id"]

            # Aymex sees it; the rival's list is empty of it.
            aymex_sites = client.get("/sites", headers=_auth(aymex["token"])).json()
            rival_sites = client.get("/sites", headers=_auth(rival["token"])).json()
            assert any(s["id"] == site_id for s in aymex_sites)
            assert not any(s["id"] == site_id for s in rival_sites)

            # And an owned site never shows up in the unauthenticated list.
            anon_sites = client.get("/sites").json()
            assert not any(s["id"] == site_id for s in anon_sites)
        finally:
            _cleanup_user(aymex["user"]["id"])
            _cleanup_user(rival["user"]["id"])


def test_owned_site_data_is_unreachable_by_others() -> None:
    """The isolation property, end to end: audience, campaigns, analytics."""
    with TestClient(app) as client:
        aymex = _register(client, "Aymex")
        rival = _register(client, "Rival Corp")
        try:
            site_id = client.post(
                "/sites",
                json={"name": "Aymex", "url": "https://aymex.example"},
                headers=_auth(aymex["token"]),
            ).json()["site"]["id"]

            probes = (
                f"/sites/{site_id}",
                f"/sites/{site_id}/audience/summary",
                f"/sites/{site_id}/visitors",
                f"/sites/{site_id}/segments",
                f"/sites/{site_id}/campaigns",
                f"/sites/{site_id}/analytics/funnel",
                f"/sites/{site_id}/content",
            )
            for path in probes:
                # The owner gets through.
                assert client.get(path, headers=_auth(aymex["token"])).status_code == 200, path
                # Another company gets 404 — not 403, which would confirm
                # the site exists.
                assert client.get(path, headers=_auth(rival["token"])).status_code == 404, path
                # So does an unauthenticated caller.
                assert client.get(path).status_code == 404, path
        finally:
            _cleanup_user(aymex["user"]["id"])
            _cleanup_user(rival["user"]["id"])


def test_public_tracking_routes_need_no_login() -> None:
    """The snippet on the customer's website must keep working regardless of
    dashboard sessions — visitors are not logged in to anything."""
    with TestClient(app) as client:
        aymex = _register(client, "Aymex")
        try:
            created = client.post(
                "/sites",
                json={"name": "Aymex", "url": "https://aymex.example"},
                headers=_auth(aymex["token"]),
            ).json()
            site_key = created["site"]["site_key"]

            # An anonymous visitor event lands without any Authorization.
            res = client.post(
                "/collect",
                content='{"site_key": "%s", "visitor_uid": "v-anon-1", '
                        '"events": [{"type": "page_view", "path": "/"}]}' % site_key,
                headers={"Content-Type": "text/plain"},
            )
            assert res.status_code in (200, 204)

            # And it reached the OWNED site even though the sender had no token.
            summary = client.get(
                f"/sites/{created['site']['id']}/audience/summary",
                headers=_auth(aymex["token"]),
            ).json()
            assert summary["totals"]["visitors"] >= 1
        finally:
            _cleanup_user(aymex["user"]["id"])


def test_password_hashes_are_salted_scrypt() -> None:
    from api import auth as auth_svc

    h1 = auth_svc.hash_password("same-password")
    h2 = auth_svc.hash_password("same-password")
    assert h1 != h2, "two hashes of one password must differ (unique salts)"
    assert h1.startswith("scrypt$")
    assert auth_svc.verify_password("same-password", h1)
    assert not auth_svc.verify_password("other-password", h1)
    assert not auth_svc.verify_password("same-password", "garbage")
