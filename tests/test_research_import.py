"""The dataset importer — the claim the whole study rests on.

If the importer distorts the dataset, every number downstream is wrong and
nothing else in this suite would notice. So these tests check the one property
that matters: **the totals the dataset measured survive the import exactly.**

They also pin the two guarantees that keep the research honest:

*   the import is deterministic and idempotent, so a rerun cannot quietly change
    a published result;
*   no imported customer can ever be emailed, whatever the SMTP configuration.
"""

from __future__ import annotations

import pandas as pd
import pytest

pytest.importorskip("fastapi")

from api import db  # noqa: E402
from api.routers.visitors import VISITOR_FEATURES_SQL  # noqa: E402

try:
    db.ping()
    DB_UP = True
except Exception:
    DB_UP = False

pytestmark = pytest.mark.skipif(not DB_UP, reason="PostgreSQL is not running")

#: Enough customers to exercise the paths that matter (zero-visit customers,
#: multi-purchase customers) without making the suite slow.
SAMPLE = 250


@pytest.fixture(scope="module")
def imported():
    """A scratch site with the first `SAMPLE` dataset customers imported."""
    import scripts.import_research_audience as importer

    db.init_schema()
    row = db.fetch_one(
        """
        INSERT INTO sites (site_key, ingest_secret, name, url)
        VALUES ('mos_test_import', 'secret', 'Import Test',
                'http://localhost:4000')
        RETURNING id
        """)
    site_id = int(row["id"])

    source = pd.read_csv(importer.DATASET).head(SAMPLE)
    from datetime import datetime, timezone
    rows = importer.build_rows(source, site_id, datetime.now(timezone.utc))
    importer._insert(rows, site_id)

    features = pd.DataFrame(db.fetch_all(VISITOR_FEATURES_SQL, site_id=site_id))
    features["CustomerID"] = (
        features["visitor_uid"].str.removeprefix("ds-").astype(int))
    merged = features.merge(source, on="CustomerID")

    yield {"site_id": site_id, "source": source, "merged": merged,
           "importer": importer}

    db.execute("DELETE FROM sites WHERE id = :i", i=site_id)


def test_every_customer_is_imported_once(imported) -> None:
    assert len(imported["merged"]) == SAMPLE


# ── Fidelity: the dataset's own numbers must survive ─────────────────────────

def test_sessions_match_website_visits(imported) -> None:
    m = imported["merged"]
    assert (m["sessions"] == m["WebsiteVisits"]).all(), (
        "a customer's visit count is a measurement; the importer may not change it")


def test_page_views_match_visits_times_pages_per_visit(imported) -> None:
    m = imported["merged"]
    expected = (m["WebsiteVisits"] * m["PagesPerVisit"]).round()
    assert (m["page_views"].round() == expected).all()


def test_time_on_site_matches_the_dataset(imported) -> None:
    m = imported["merged"]
    expected = m["WebsiteVisits"] * m["TimeOnSite"] * 60
    # Rounding each visit's dwell time would accumulate across a customer with
    # 49 visits, which is why the importer stores it unrounded.
    assert ((m["time_on_site_seconds"] - expected).abs() < 0.01).all()


def test_purchases_match_previous_purchases(imported) -> None:
    m = imported["merged"]
    assert (m["purchases"] == m["PreviousPurchases"]).all()


def test_customers_with_no_visits_get_no_sessions(imported) -> None:
    """A customer the dataset never saw on the website must not gain a visit.

    They can still have an email history and previous purchases — which is why
    the importer writes those without attaching them to an invented session.
    """
    m = imported["merged"]
    never_visited = m[m["WebsiteVisits"] == 0]
    if never_visited.empty:
        pytest.skip("no zero-visit customers in this sample")
    assert (never_visited["sessions"] == 0).all()


def test_email_history_becomes_interactions(imported) -> None:
    counts = db.fetch_one(
        """
        SELECT count(*) FILTER (WHERE event_type = 'open')    AS opens,
               count(*) FILTER (WHERE event_type = 'click')   AS clicks,
               count(*) FILTER (WHERE event_type = 'convert') AS converts
        FROM interactions WHERE site_id = :s
        """, s=imported["site_id"])
    source = imported["source"]

    assert counts["opens"] == int(source["EmailOpens"].sum())
    assert counts["clicks"] == int(source["EmailClicks"].sum())
    assert counts["converts"] == int(source["Conversion"].sum())


def test_email_interactions_belong_to_no_campaign(imported) -> None:
    """Dataset email history predates this system, so it must not be counted
    in the funnel of a campaign this system planned — only in attribution."""
    stray = db.fetch_one(
        """SELECT count(*) AS n FROM interactions
           WHERE site_id = :s AND source = 'dataset' AND campaign_id IS NOT NULL""",
        s=imported["site_id"])
    assert stray["n"] == 0


# ── Provenance ───────────────────────────────────────────────────────────────

def test_everything_imported_is_labelled_dataset(imported) -> None:
    bad = db.fetch_one(
        """
        SELECT (SELECT count(*) FROM visitors
                 WHERE site_id = :s AND source <> 'dataset')     AS visitors,
               (SELECT count(*) FROM interactions
                 WHERE site_id = :s AND source <> 'dataset')     AS interactions
        """, s=imported["site_id"])
    assert bad["visitors"] == 0 and bad["interactions"] == 0


def test_no_imported_customer_can_be_emailed_for_real(imported) -> None:
    """The one guarantee that must hold whatever `.env` says.

    Every imported address uses the reserved `.invalid` TLD (RFC 2606), which
    cannot resolve. Even with SMTP configured and consent granted, this audience
    is unreachable by construction rather than by policy.
    """
    reachable = db.fetch_one(
        """
        SELECT count(*) AS n FROM visitors
        WHERE site_id = :s AND email IS NOT NULL
          AND email NOT LIKE '%%@example.invalid'
        """, s=imported["site_id"])
    assert reachable["n"] == 0

    consenting = db.fetch_one(
        "SELECT count(*) AS n FROM visitors WHERE site_id = :s AND email_consent",
        s=imported["site_id"])
    assert consenting["n"] > 0, "the sample should contain contactable customers"


# ── Reproducibility ──────────────────────────────────────────────────────────

def test_import_is_deterministic(imported) -> None:
    """Same CSV in, same features out — a published number cannot drift."""
    from datetime import datetime, timezone

    importer = imported["importer"]
    site_id = imported["site_id"]

    before = pd.DataFrame(db.fetch_all(VISITOR_FEATURES_SQL, site_id=site_id))

    importer._clear_dataset_visitors(site_id)
    rows = importer.build_rows(imported["source"], site_id,
                               datetime.now(timezone.utc))
    importer._insert(rows, site_id)

    after = pd.DataFrame(db.fetch_all(VISITOR_FEATURES_SQL, site_id=site_id))

    columns = ["page_views", "clicks", "sessions", "unique_pages",
               "max_scroll_depth", "time_on_site_seconds", "form_submits",
               "purchases"]
    left = before.sort_values("visitor_uid")[columns].reset_index(drop=True)
    right = after.sort_values("visitor_uid")[columns].reset_index(drop=True)
    pd.testing.assert_frame_equal(left, right)


def test_clearing_removes_only_imported_customers(imported) -> None:
    site_id = imported["site_id"]
    importer = imported["importer"]

    db.execute(
        """INSERT INTO visitors (site_id, visitor_uid, source)
           VALUES (:s, 'a-live-browser', 'live')""", s=site_id)

    importer._clear_dataset_visitors(site_id)

    remaining = db.fetch_all(
        "SELECT visitor_uid, source FROM visitors WHERE site_id = :s", s=site_id)
    assert [r["visitor_uid"] for r in remaining] == ["a-live-browser"]

    # Restore the fixture's state for any test that runs after this one.
    from datetime import datetime, timezone
    db.execute("DELETE FROM visitors WHERE site_id = :s", s=site_id)
    rows = importer.build_rows(imported["source"], site_id,
                               datetime.now(timezone.utc))
    importer._insert(rows, site_id)


# ── The shared feature definition ────────────────────────────────────────────

def test_one_feature_definition_serves_both_audiences() -> None:
    """A live browser reports one page view per page and no count; the importer
    reports one event per visit carrying that visit's total. The SQL must sum
    the two identically, or the two audiences would not be comparable."""
    assert "props->>'pages'" in VISITOR_FEATURES_SQL
    assert "COALESCE((e.props->>'pages')::float8, 1)" in VISITOR_FEATURES_SQL, (
        "the fallback to 1 is what makes a live browser's event count correctly")
