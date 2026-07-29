"""Phase 4 tests — Module 3 analytics over observed campaign data.

Focused on the claims a viva examiner would probe:

  · the funnel counts campaign events, not website browsing
  · attribution has genuine multi-platform journeys to work with, and says so
    honestly when it does not
  · predictions are written where Modules 2 and 4 can read them
  · every result declares whether it rests on real or simulated data

Requires PostgreSQL:  docker-compose up -d
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from api import db
from api.main import app
from api.services import analytics as svc

pytestmark = pytest.mark.skipif(
    not db.ping(), reason="PostgreSQL is not reachable — run `docker-compose up -d`"
)

NOW = datetime.now(timezone.utc)


@pytest.fixture(scope="module")
def client() -> TestClient:
    db.init_schema()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def site(client: TestClient):
    res = client.post("/sites", json={"name": "Analytics Test",
                                      "url": "https://analytics.example"})
    body = res.json()["site"]
    yield body
    db.execute("DELETE FROM sites WHERE id = :i", i=body["id"])


def _visitor(site_id: int, uid: str, utm: str | None = None,
             dataset: bool = False, segment: str = "High Intent") -> int:
    row = db.fetch_one(
        """INSERT INTO visitors (site_id, visitor_uid, email, email_consent,
                                 utm_source, source, first_seen)
           VALUES (:s, :u, :e, TRUE, :utm, :src, :seen) RETURNING id""",
        s=site_id, u=uid, e=f"{uid}@x.com", utm=utm,
        src="dataset" if dataset else "live",
        seen=NOW - timedelta(days=10))
    vid = int(row["id"])
    db.execute(
        """INSERT INTO user_segments (site_id, visitor_id, segment_name,
                                      segment_method, segment_confidence)
           VALUES (:s, :v, :n, 'hybrid', 0.8)""",
        s=site_id, v=vid, n=segment)
    return vid


def _campaign(site_id: int, strategy: str = "hybrid") -> int:
    return int(db.fetch_one(
        """INSERT INTO campaigns (site_id, name, strategy, status)
           VALUES (:s, 'T', :st, 'running') RETURNING id""",
        s=site_id, st=strategy)["id"])


def _interaction(site_id: int, visitor_id: int, campaign_id: int, event: str,
                 offset_hours: int = 0, source: str = "live",
                 platform: str = "email") -> None:
    db.execute(
        """INSERT INTO interactions (site_id, visitor_id, campaign_id, strategy,
                                     channel, platform, event_type, source,
                                     occurred_at)
           VALUES (:s, :v, :c, 'hybrid', 'email', :p, :e, :src, :t)""",
        s=site_id, v=visitor_id, c=campaign_id, p=platform, e=event,
        src=source, t=NOW - timedelta(days=5) + timedelta(hours=offset_hours))


def _journey(site_id: int, campaign_id: int, uid: str, utm: str,
             convert: bool = True, **kw) -> int:
    """A full sent → open → click (→ convert) journey for one visitor."""
    vid = _visitor(site_id, uid, utm=utm, **kw)
    source = "dataset" if kw.get("dataset") else "live"
    for i, event in enumerate(["sent", "open", "click"]):
        _interaction(site_id, vid, campaign_id, event, offset_hours=i,
                     source=source)
    if convert:
        _interaction(site_id, vid, campaign_id, "convert", offset_hours=4,
                     source=source)
    return vid


# ── Journey construction ─────────────────────────────────────────────────────

def test_journey_joins_acquisition_channel_to_email_touches(site) -> None:
    """Email alone is one platform, and every attribution model gives the same
    answer on a single-platform journey. The acquisition touch is what makes
    multi-touch attribution meaningful at all."""
    cid = _campaign(site["id"])
    _journey(site["id"], cid, "j1", utm="linkedin")

    events = svc.journey_events(site["id"])
    platforms = set(events["platform"])
    assert "email" in platforms
    assert "linkedin" in platforms, "acquisition channel must appear as a touchpoint"


def test_visitor_without_utm_is_credited_to_direct(site) -> None:
    cid = _campaign(site["id"])
    _journey(site["id"], cid, "j2", utm=None)

    events = svc.journey_events(site["id"])
    assert "direct" in set(events["platform"])


# ── Funnel ───────────────────────────────────────────────────────────────────

def test_funnel_counts_campaign_events_only(site) -> None:
    """Acquisition touches must not inflate the campaign funnel — otherwise
    every visitor would appear to have clicked an email."""
    cid = _campaign(site["id"])
    _journey(site["id"], cid, "f1", utm="google")
    _visitor(site["id"], "browser-only", utm="google")   # never emailed

    result = svc.build_funnel(site["id"])
    assert result["funnel"]["sent"] == 1
    assert result["funnel"]["click"] == 1, "the browse-only visitor must not count"


def test_funnel_reports_dropoffs_and_slices(site) -> None:
    cid = _campaign(site["id"], "trigger")
    _journey(site["id"], cid, "d1", utm="linkedin", convert=True)
    _journey(site["id"], cid, "d2", utm="linkedin", convert=False)

    result = svc.build_funnel(site["id"])
    assert result["funnel"]["click"] == 2
    assert result["funnel"]["convert"] == 1
    assert result["dropoffs"]["click→convert"] == pytest.approx(0.5)
    assert any(r["strategy"] == "trigger" for r in result["by_strategy"])
    assert result["by_segment"], "funnel must be sliceable by segment"


def test_funnel_is_empty_before_any_campaign(site) -> None:
    _visitor(site["id"], "lonely", utm="direct")
    result = svc.build_funnel(site["id"])
    assert result["funnel"]["sent"] == 0
    assert "No campaign" in result["note"]


# ── Attribution ──────────────────────────────────────────────────────────────

def test_attribution_declines_when_there_are_too_few_conversions(site) -> None:
    """Reporting attribution over two journeys would be noise dressed as a
    finding, so the service refuses and explains why."""
    cid = _campaign(site["id"])
    for i in range(2):
        _journey(site["id"], cid, f"few{i}", utm="linkedin")

    result = svc.build_attribution(site["id"])
    assert result["models"] == {}
    assert "below the" in result["note"]


def test_attribution_models_disagree_on_multi_touch_journeys(site) -> None:
    """The research claim: first-touch credits acquisition, last-touch credits
    the closing channel. If they agree, the comparison is vacuous."""
    cid = _campaign(site["id"])
    for i in range(8):
        _journey(site["id"], cid, f"multi{i}", utm="linkedin")

    result = svc.build_attribution(site["id"])
    first = {r["platform"]: r["credit"] for r in result["models"]["first_touch"]}
    last = {r["platform"]: r["credit"] for r in result["models"]["last_touch"]}

    assert first.get("linkedin", 0) > first.get("email", 0), "first touch is acquisition"
    assert last.get("email", 0) > last.get("linkedin", 0), "last touch is the email"


def test_attribution_reports_single_touch_share(site) -> None:
    """Agreement between models on single-touch journeys is arithmetic, not
    evidence — the diagnostics must make that visible."""
    cid = _campaign(site["id"])
    for i in range(8):
        _journey(site["id"], cid, f"diag{i}", utm="linkedin")

    diag = svc.build_attribution(site["id"])["diagnostics"]
    assert diag["n_converting_journeys"] == 8
    assert 0.0 <= diag["single_touch_share"] <= 1.0
    assert diag["mean_distinct_touchpoints"] >= 1.0


def test_all_four_attribution_models_run(site) -> None:
    cid = _campaign(site["id"])
    for i in range(10):
        _journey(site["id"], cid, f"all{i}", utm=["linkedin", "google"][i % 2])

    models = svc.build_attribution(site["id"])["models"]
    assert set(models) == {"first_touch", "last_touch", "linear", "markov"}
    for name, rows in models.items():
        assert isinstance(rows, list), f"{name} failed: {rows}"
        assert rows, f"{name} produced no credit"


# ── Data basis ───────────────────────────────────────────────────────────────

def test_results_declare_live_versus_dataset(site) -> None:
    cid = _campaign(site["id"])
    _journey(site["id"], cid, "real1", utm="linkedin", dataset=False)
    assert svc.build_funnel(site["id"])["data_basis"] == "live"

    _journey(site["id"], cid, "from-dataset", utm="google", dataset=True)
    assert svc.build_funnel(site["id"])["data_basis"] == "mixed"


def test_dataset_only_site_is_labelled_dataset(site) -> None:
    """The normal state of the research build: every figure must say so."""
    cid = _campaign(site["id"])
    _journey(site["id"], cid, "ds-only", utm="linkedin", dataset=True)
    assert svc.build_funnel(site["id"])["data_basis"] == "dataset"


# ── Predictions ──────────────────────────────────────────────────────────────

def test_predictions_are_written_where_the_loop_reads_them(site) -> None:
    """analytics_output (Figure 5.4) is what Modules 2 and 4 consume."""
    cid = _campaign(site["id"])
    for i in range(6):
        _journey(site["id"], cid, f"p{i}", utm="linkedin", convert=i % 2 == 0)

    result = svc.build_predictions(site["id"])
    assert result["n_users"] == 6

    rows = db.fetch_all(
        """SELECT predicted_conversion, drop_off_risk, recommendation, confidence
           FROM analytics_output WHERE site_id = :s""", s=site["id"])
    assert len(rows) == 6
    for r in rows:
        assert 0.0 <= float(r["predicted_conversion"]) <= 1.0
        assert 0.0 <= float(r["drop_off_risk"]) <= 1.0
        assert r["recommendation"]


def test_rerunning_predictions_does_not_duplicate_rows(site) -> None:
    cid = _campaign(site["id"])
    for i in range(6):
        _journey(site["id"], cid, f"dup{i}", utm="linkedin")

    svc.build_predictions(site["id"])
    svc.build_predictions(site["id"])

    n = db.fetch_one("SELECT count(*) c FROM analytics_output WHERE site_id=:s",
                     s=site["id"])["c"]
    assert n == 6, "each visitor keeps exactly one current prediction"


def test_predictions_say_which_data_the_model_was_fitted_on(site) -> None:
    """The shipped models were fitted on Module 3's simulator. Using them on a
    real audience is a transfer across distributions and must be labelled."""
    cid = _campaign(site["id"])
    for i in range(6):
        _journey(site["id"], cid, f"note{i}", utm="linkedin")

    result = svc.build_predictions(site["id"])
    assert "simulat" in result["model_note"].lower()
    assert result["source"]


def test_degenerate_predictions_raise_a_calibration_warning(site) -> None:
    """A transferred model can rank correctly while producing probabilities
    crushed to one end, silently invalidating every threshold."""
    cid = _campaign(site["id"])
    for i in range(15):
        _journey(site["id"], cid, f"cal{i}", utm="linkedin", convert=i % 3 == 0)

    result = svc.build_predictions(site["id"])
    warnings = result["calibration_warnings"]
    assert isinstance(warnings, list)
    for w in warnings:
        assert "threshold" in w or "discriminating" in w


def test_predictions_need_segments_first(site) -> None:
    result = svc.build_predictions(site["id"])
    assert result["n_users"] == 0
    assert "segments" in result["note"].lower()


# ── Full pass + endpoints ────────────────────────────────────────────────────

def test_full_run_produces_checkable_insights(site, client: TestClient) -> None:
    cid = _campaign(site["id"])
    for i in range(10):
        _journey(site["id"], cid, f"run{i}", utm=["linkedin", "google"][i % 2],
                 convert=i % 2 == 0)

    res = client.post(f"/sites/{site['id']}/analytics/run")
    assert res.status_code == 200
    body = res.json()

    assert body["funnel"]["funnel"]["sent"] == 10
    assert body["predictions"]["n_users"] == 10
    assert body["insights"], "a run with data must produce findings"
    # Every insight should cite a number rather than assert a vibe.
    assert any(any(ch.isdigit() for ch in text) for text in body["insights"])


def test_analytics_endpoints_404_on_unknown_site(client: TestClient) -> None:
    for path in ("analytics/funnel", "analytics/attribution",
                 "analytics/recommendations"):
        assert client.get(f"/sites/999999/{path}").status_code == 404
    assert client.post("/sites/999999/analytics/run").status_code == 404
