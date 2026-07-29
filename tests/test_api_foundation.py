"""Phase 0 smoke tests for the FastAPI backend.

These need PostgreSQL running:

    docker-compose up -d
    venv/bin/pytest tests/test_api_foundation.py -v

They are skipped (not failed) when the database is unreachable, so the rest of
the research test-suite still runs on a machine without Docker.
"""

from __future__ import annotations

import pytest

from api import db
from api.settings import get_settings

pytestmark = pytest.mark.skipif(
    not db.ping(), reason="PostgreSQL is not reachable — run `docker-compose up -d`"
)

# Tables the report's architecture figures name explicitly.
REPORT_TABLES = {
    "user_segments",     # Figure 5.2 — Segments Table
    "interactions",      # Figure 5.3 — Interactions Table
    "analytics_output",  # Figure 5.4 — Analytics Output
    "content_assets",    # Figure 5.5 — Content Assets Table
}

SUPPORTING_TABLES = {
    "sites", "visitors", "events", "site_crawls",
    "campaigns", "campaign_sends", "pipeline_runs",
}


@pytest.fixture(scope="module", autouse=True)
def _schema() -> None:
    db.init_schema()


def _table_names() -> set[str]:
    rows = db.fetch_all(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    )
    return {r["table_name"] for r in rows}


def test_schema_is_idempotent() -> None:
    """schema.sql is applied on every boot, so re-running must never fail."""
    db.init_schema()
    db.init_schema()


def test_report_tables_exist() -> None:
    missing = REPORT_TABLES - _table_names()
    assert not missing, f"tables named in the report figures are missing: {missing}"


def test_supporting_tables_exist() -> None:
    missing = SUPPORTING_TABLES - _table_names()
    assert not missing, f"supporting tables missing: {missing}"


def test_email_consent_defaults_to_false() -> None:
    """No visitor may ever be emailable by default — consent is opt-in only."""
    row = db.fetch_one(
        """
        SELECT column_default, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'visitors' AND column_name = 'email_consent'
        """
    )
    assert row is not None
    assert "false" in str(row["column_default"]).lower()
    assert row["is_nullable"] == "NO"


def test_interactions_record_their_provenance() -> None:
    """The funnel table must distinguish events produced by a live browser from
    those reconstructed from the research dataset, so an experiment can never be
    mistaken for a measurement of live behaviour."""
    row = db.fetch_one(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'interactions' AND column_name = 'source'
        """
    )
    assert row is not None, "interactions.source is required for honest reporting"


def test_api_health_endpoint() -> None:
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ok"
        assert body["database"] == "up"


def test_site_registration_returns_snippet() -> None:
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as client:
        res = client.post(
            "/sites",
            json={"name": "Test Site", "url": "https://example.com"},
        )
        assert res.status_code == 201
        body = res.json()
        site_key = body["site"]["site_key"]

        assert site_key.startswith("mos_")
        # The snippet must carry the public key and never the private secret.
        assert site_key in body["snippet"]
        assert body["ingest_secret"] not in body["snippet"]
        assert get_settings().public_api_url in body["snippet"]

    # clean up so repeated runs do not accumulate rows
    db.execute("DELETE FROM sites WHERE site_key = :k", k=site_key)


def test_numeric_columns_are_never_serialised_as_strings() -> None:
    """Postgres NUMERIC arrives in JSON as a *string*, not a number.

    That has broken this project twice: once turning model features into text,
    once crashing the dashboard on `.toFixed()`. Any endpoint exposing a
    NUMERIC column must cast it to float8. This test asserts the rule at the
    schema level so a new query cannot reintroduce it silently.
    """
    from fastapi.testclient import TestClient

    from api.main import app

    numeric_columns = db.fetch_all(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND data_type = 'numeric'
        ORDER BY table_name, column_name
        """
    )
    # The schema does use NUMERIC for stored precision — that is fine. What
    # matters is that responses convert it.
    assert numeric_columns, "expected NUMERIC columns to exist in the schema"

    with TestClient(app) as client:
        site = client.post(
            "/sites", json={"name": "Numeric Probe", "url": "https://probe.example"}
        ).json()["site"]

        try:
            for path in (
                f"/sites/{site['id']}/audience/summary",
                f"/sites/{site['id']}/visitors",
                f"/sites/{site['id']}/segments",
                f"/sites/{site['id']}/analytics/recommendations",
            ):
                res = client.get(path)
                assert res.status_code == 200, path
                _assert_no_numeric_strings(res.json(), path)
        finally:
            db.execute("DELETE FROM sites WHERE id = :i", i=site["id"])


def _assert_no_numeric_strings(node: object, path: str, key: str = "") -> None:
    """Walk a response and fail on any value that looks like a stringified number."""
    if isinstance(node, dict):
        for k, v in node.items():
            _assert_no_numeric_strings(v, path, k)
    elif isinstance(node, list):
        for item in node:
            _assert_no_numeric_strings(item, path, key)
    elif isinstance(node, str):
        # Bare decimals only. Dates, ids and free text are unaffected.
        stripped = node.strip()
        looks_numeric = (
            stripped.replace(".", "", 1).replace("-", "", 1).isdigit()
            and "." in stripped
        )
        assert not looks_numeric, (
            f"{path}: field '{key}' returned {node!r} as a string — "
            "cast the NUMERIC column to float8"
        )
