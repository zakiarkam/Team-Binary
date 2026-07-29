#!/usr/bin/env python
"""Import the research dataset as the demo store's customer base.

    venv/bin/python scripts/import_research_audience.py --site-id 1
    venv/bin/python scripts/import_research_audience.py --site-id 1 --limit 500
    venv/bin/python scripts/import_research_audience.py --site-id 1 --clear

WHAT THIS DOES
--------------
Each of the 8,000 rows in the *Digital Marketing Campaign* dataset becomes one
customer of the Innov8Smart store, with the behaviour that row records. After
this runs, every module operates on that audience: Module 1 segments it,
Module 2 plans campaigns for it, Module 3 analyses its funnel, Module 4 writes
content for it.

WHAT IS DATA AND WHAT IS RECONSTRUCTION — read this before quoting any number
----------------------------------------------------------------------------
The dataset is real: 8,000 real people, whose behaviour was really measured.
But it was measured as **per-customer totals** — "25 website visits, 5.5 pages
per visit, 7.7 minutes on site, 9 email opens, 4 email clicks". It is not an
event log. Nobody recorded *when* visit 14 happened or *which* page it was.

So this importer preserves the totals exactly and reconstructs only what the
dataset never contained:

    EXACT (taken straight from the dataset, never altered)
      sessions          = WebsiteVisits
      page_views        = WebsiteVisits × PagesPerVisit
      time_on_site      = WebsiteVisits × TimeOnSite (minutes → seconds)
      clicks            = ClickThroughRate × page_views
      purchases         = PreviousPurchases
      email opens       = EmailOpens          (one interaction row each)
      email clicks      = EmailClicks         (one interaction row each)
      converted         = Conversion          (one interaction row if 1)
      acquisition channel = CampaignChannel

    RECONSTRUCTED (invented here, because the dataset has no such column)
      the timestamp of each visit      — spread over a 90-day window
      which page each visit landed on  — cycled through the store's real pages
      scroll depth                     — derived from time-on-site
      the order of email opens/clicks  — interleaved through the window

Anything that depends only on the totals — segment membership, conversion rate
by segment, funnel counts — rests on real measurements. Anything that depends
on event ORDER or TIMING — attribution paths, journey length, inter-event gaps
— is a property of this reconstruction as much as of the data, and must be
reported that way. `docs/research/methodology.md` states this; so does the
Research page in the dashboard.

To keep that distinction visible in the data itself rather than only in prose,
one event is written per *visit* carrying that visit's page count, instead of
one event per page view. A live browser reports one event per page and no
count, and `VISITOR_FEATURES_SQL` sums the two identically — so the same
feature definition serves both without either pretending to be the other.

DESIGN NOTES
------------
*   Deterministic. All randomness is seeded from the CustomerID, so the same
    CSV always produces the same database. Re-running changes nothing.
*   Idempotent. Existing dataset visitors for the site are removed first
    (cascading to their events and interactions); live visitors are untouched.
*   Email addresses use the reserved `.invalid` TLD (RFC 2606), which can never
    resolve. Even with SMTP configured, this audience is unreachable by design.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import openmp_guard  # noqa: F401,E402  (import order matters — see the module)

import pandas as pd  # noqa: E402

from api import db  # noqa: E402

DATASET = ROOT / "modules" / "m1_segmentation" / "digital_marketing_campaign_dataset.csv"

#: The store's real pages. Visits are cycled through these, so a customer with
#: more visits has seen more of the site — which is what `unique_pages` means.
STORE_PAGES = [
    "/index.html",
    "/product-nimbus-plug.html",
    "/product-lumen-light.html",
    "/cart.html",
    "/product-vista-cam.html",
    "/product-aura-hub.html",
    "/product-terra-climate.html",
    "/product-pulse-sensor.html",
]

#: Catalogue prices, used to give each recorded purchase a plausible value.
#: The dataset counts purchases but does not price them, so the *count* is data
#: and the basket value is illustrative only.
PRICES = [24, 29, 34, 39, 89, 129]

#: CampaignChannel → the acquisition channel stored on the visitor.
#:
#: Kept deliberately faithful to the dataset's own vocabulary. It is tempting to
#: rename "Social Media" to "instagram" so that attribution credit lands on a
#: platform this system can publish to — and that would make the closed loop
#: look better. It would also be a fabrication: the dataset does not say which
#: social platform. Reported as-is, most attributed credit correctly turns out
#: to sit with channels the content module cannot act on, and
#: `content.platform_priorities` already says so in as many words.
CHANNEL_MAP = {
    "Social Media": "social_media",
    "Email": "email",
    "PPC": "ppc",
    "SEO": "seo",
    "Referral": "referral",
}

#: How far back the reconstructed history runs.
WINDOW_DAYS = 90


def _clear_dataset_visitors(site_id: int) -> int:
    """Remove previously imported customers. Live visitors are left alone."""
    row = db.fetch_one(
        "SELECT count(*) AS n FROM visitors WHERE site_id = :s AND source = 'dataset'",
        s=site_id)
    n = (row or {}).get("n", 0)
    if n:
        # events, interactions, user_segments and analytics_output all cascade.
        db.execute("DELETE FROM visitors WHERE site_id = :s AND source = 'dataset'",
                   s=site_id)
    return n


def _visit_schedule(n_visits: int, rng: random.Random,
                    now: datetime) -> list[datetime]:
    """Timestamps for one customer's visits, oldest first.

    RECONSTRUCTED. The dataset records how many visits happened, never when.
    They are spread over the window with a mild recency bias, because a
    customer's activity realistically clusters nearer the present — but that
    shape is an assumption of this importer, not a finding from the data.
    """
    if n_visits <= 0:
        return []
    stamps = []
    for _ in range(n_visits):
        # rng.random() ** 1.6 biases towards 0, i.e. towards "recently".
        age_days = (rng.random() ** 1.6) * WINDOW_DAYS
        stamps.append(now - timedelta(days=age_days))
    return sorted(stamps)


def _scroll_depth(minutes_on_page: float, rng: random.Random) -> int:
    """Derived from dwell time, in the same 25/50/75/100 buckets mos.js emits."""
    if minutes_on_page >= 10:
        base = 100
    elif minutes_on_page >= 6:
        base = 75
    elif minutes_on_page >= 3:
        base = 50
    else:
        base = 25
    # One bucket of jitter, so depth is not a deterministic function of time.
    return int(min(100, max(25, base + rng.choice([-25, 0, 0, 0, 25]))))


def build_rows(df: pd.DataFrame, site_id: int, now: datetime) -> dict[str, list]:
    """Turn dataset rows into visitor / event / interaction rows.

    Pure: does no I/O, so it can be unit-tested against a small frame.
    """
    visitors, events, interactions = [], [], []

    for record in df.to_dict("records"):
        cid = int(record["CustomerID"])
        rng = random.Random(cid)          # deterministic per customer

        visits = int(record["WebsiteVisits"])
        pages_per_visit = float(record["PagesPerVisit"])
        minutes_per_visit = float(record["TimeOnSite"])
        ctr = float(record["ClickThroughRate"])
        purchases = int(record["PreviousPurchases"])
        opens = int(record["EmailOpens"])
        clicks_email = int(record["EmailClicks"])
        converted = int(record["Conversion"]) == 1

        # Any recorded email engagement means this person was on the shop's
        # mailing list, so they are modelled as having opted in. Someone with no
        # opens and no clicks is not assumed to be contactable.
        consent = opens > 0 or clicks_email > 0

        schedule = _visit_schedule(visits, rng, now)
        first_seen = schedule[0] if schedule else now - timedelta(days=WINDOW_DAYS)
        last_seen = schedule[-1] if schedule else first_seen

        uid = f"ds-{cid}"
        visitors.append({
            "site_id": site_id,
            "visitor_uid": uid,
            "email": f"customer{cid}@example.invalid" if consent else None,
            "name": None,
            "email_consent": consent,
            "consent_at": first_seen if consent else None,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "utm_source": CHANNEL_MAP.get(str(record["CampaignChannel"]), "direct"),
            "utm_medium": "campaign",
            "utm_campaign": str(record["CampaignType"]).lower(),
            "referrer": None,
            "device": rng.choice(["desktop", "mobile", "mobile", "tablet"]),
            "source": "dataset",
            "attributes": json.dumps({
                "customer_id": cid,
                "age": int(record["Age"]),
                "gender": str(record["Gender"]),
                "income": float(record["Income"]),
                "campaign_channel": str(record["CampaignChannel"]),
                "campaign_type": str(record["CampaignType"]),
                "ad_spend": float(record["AdSpend"]),
                "social_shares": int(record["SocialShares"]),
                "loyalty_points": int(record["LoyaltyPoints"]),
                # Recorded email behaviour, kept on the visitor so a campaign
                # response model can be grounded in what this specific person
                # actually did rather than in one rate applied to everybody.
                "email_opens": opens,
                "email_clicks": clicks_email,
                "dataset_conversion": int(record["Conversion"]),
                "dataset_conversion_rate": float(record["ConversionRate"]),
            }),
        })

        # ── On-site behaviour: one event per visit, carrying that visit's
        #    totals. `pages` and `count` are what VISITOR_FEATURES_SQL sums.
        total_pages = round(visits * pages_per_visit)
        total_clicks = round(ctr * total_pages)
        for i, when in enumerate(schedule):
            session = f"ds{cid}-{i}"
            # Distribute the customer's page total across their visits, so the
            # per-visitor sum is exactly WebsiteVisits × PagesPerVisit.
            pages = total_pages // visits + (1 if i < total_pages % visits else 0)
            clicks = total_clicks // visits + (1 if i < total_clicks % visits else 0)

            events.append({
                "site_id": site_id, "visitor_uid": uid, "session_id": session,
                "event_type": "page_view", "path": STORE_PAGES[i % len(STORE_PAGES)],
                "props": json.dumps({"pages": pages, "reconstructed": True}),
                "occurred_at": when,
            })
            if clicks:
                events.append({
                    "site_id": site_id, "visitor_uid": uid, "session_id": session,
                    "event_type": "click", "path": STORE_PAGES[i % len(STORE_PAGES)],
                    "props": json.dumps({"count": clicks, "reconstructed": True}),
                    "occurred_at": when + timedelta(seconds=30),
                })
            events.append({
                "site_id": site_id, "visitor_uid": uid, "session_id": session,
                "event_type": "scroll", "path": STORE_PAGES[i % len(STORE_PAGES)],
                "props": json.dumps({"depth": _scroll_depth(minutes_per_visit, rng),
                                     "reconstructed": True}),
                "occurred_at": when + timedelta(seconds=20),
            })
            events.append({
                "site_id": site_id, "visitor_uid": uid, "session_id": session,
                "event_type": "page_exit", "path": STORE_PAGES[i % len(STORE_PAGES)],
                # Deliberately unrounded. Rounding each visit's dwell time to a
                # decimal place costs up to 0.05s per visit, and a customer with
                # 49 visits then no longer sums to the TimeOnSite the dataset
                # recorded. The totals are the part that has to stay exact.
                "props": json.dumps({"seconds": minutes_per_visit * 60,
                                     "reconstructed": True}),
                "occurred_at": when + timedelta(minutes=minutes_per_visit),
            })

        # Joining the mailing list is a form submission — but only someone who
        # actually visited the site could have used the form. A customer with
        # WebsiteVisits = 0 and an email history was already a contact of the
        # shop; inventing a form submission for them would both contradict the
        # dataset and manufacture a session they never had.
        if consent and schedule:
            events.append({
                "site_id": site_id, "visitor_uid": uid,
                "session_id": f"ds{cid}-0",
                "event_type": "form_submit", "path": "/index.html",
                "props": json.dumps({"form": "newsletter", "reconstructed": True}),
                "occurred_at": first_seen + timedelta(minutes=1),
            })

        # ── Purchases. The count is data; the basket value is illustrative.
        #    A purchase by a customer with no recorded visits carries no
        #    session, so it cannot inflate their visit count.
        for k in range(purchases):
            when = schedule[min(k, len(schedule) - 1)] if schedule else first_seen
            price = rng.choice(PRICES)
            events.append({
                "site_id": site_id, "visitor_uid": uid,
                "session_id": f"ds{cid}-{min(k, visits - 1)}" if schedule else None,
                "event_type": "purchase", "path": "/cart.html",
                "props": json.dumps({"value": price, "points_earned": price * 10,
                                     "reconstructed_value": True}),
                "occurred_at": when + timedelta(minutes=minutes_per_visit + 2),
            })

        # ── Email history. Counts are data; their placement in time is not.
        #    campaign_id stays NULL: these belong to the campaign the dataset
        #    recorded, not to any campaign this system planned, so they inform
        #    attribution without ever being counted in our own campaign funnel.
        for k in range(opens):
            interactions.append({
                "site_id": site_id, "visitor_uid": uid, "event_type": "open",
                "occurred_at": first_seen + timedelta(
                    days=(k + 1) * WINDOW_DAYS / (opens + 1)),
            })
        for k in range(clicks_email):
            interactions.append({
                "site_id": site_id, "visitor_uid": uid, "event_type": "click",
                "occurred_at": first_seen + timedelta(
                    days=(k + 1) * WINDOW_DAYS / (clicks_email + 1),
                    minutes=5),
            })
        if converted:
            interactions.append({
                "site_id": site_id, "visitor_uid": uid, "event_type": "convert",
                "occurred_at": last_seen,
            })

    return {"visitors": visitors, "events": events, "interactions": interactions}


def _insert(rows: dict[str, list], site_id: int, batch: int = 5_000) -> None:
    """Write the rows, resolving visitor_uid → visitor_id once."""
    def chunks(seq, n):
        for i in range(0, len(seq), n):
            yield seq[i:i + n]

    for part in chunks(rows["visitors"], batch):
        db.execute_many(
            """
            INSERT INTO visitors (site_id, visitor_uid, email, name, email_consent,
                                  consent_at, first_seen, last_seen, utm_source,
                                  utm_medium, utm_campaign, referrer, device,
                                  source, attributes)
            VALUES (:site_id, :visitor_uid, :email, :name, :email_consent,
                    :consent_at, :first_seen, :last_seen, :utm_source,
                    :utm_medium, :utm_campaign, :referrer, :device,
                    :source, CAST(:attributes AS jsonb))
            """, part)

    ids = {r["visitor_uid"]: r["id"] for r in db.fetch_all(
        "SELECT id, visitor_uid FROM visitors WHERE site_id = :s AND source = 'dataset'",
        s=site_id)}

    for part in chunks(rows["events"], batch):
        db.execute_many(
            """
            INSERT INTO events (site_id, visitor_id, session_id, event_type,
                                path, props, occurred_at)
            VALUES (:site_id, :visitor_id, :session_id, :event_type,
                    :path, CAST(:props AS jsonb), :occurred_at)
            """,
            [{**e, "visitor_id": ids[e.pop("visitor_uid")]} for e in part])

    for part in chunks(rows["interactions"], batch):
        db.execute_many(
            """
            INSERT INTO interactions (site_id, visitor_id, campaign_id, channel,
                                      platform, event_type, source, meta,
                                      occurred_at)
            VALUES (:site_id, :visitor_id, NULL, 'email', 'email', :event_type,
                    'dataset', CAST(:meta AS jsonb), :occurred_at)
            """,
            [{**i, "visitor_id": ids[i.pop("visitor_uid")],
              "meta": json.dumps({"from_dataset": True})} for i in part])


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site-id", type=int, default=1)
    ap.add_argument("--dataset", default=str(DATASET))
    ap.add_argument("--limit", type=int, default=None,
                    help="Import only the first N customers (for a quick run)")
    ap.add_argument("--clear", action="store_true",
                    help="Remove imported customers and exit")
    args = ap.parse_args()

    site = db.fetch_one("SELECT id, name FROM sites WHERE id = :i", i=args.site_id)
    if site is None:
        print(f"✗ Site {args.site_id} does not exist. Run setup_demo_site.py first.",
              file=sys.stderr)
        return 1

    removed = _clear_dataset_visitors(args.site_id)
    if removed:
        print(f"Removed {removed:,} previously imported customers")
    if args.clear:
        return 0

    df = pd.read_csv(args.dataset)
    if args.limit:
        df = df.head(args.limit)
    print(f"Read {len(df):,} customers from {Path(args.dataset).name}")

    # Fixed reference point: the reconstruction hangs off "now", but everything
    # within it is deterministic given the CustomerID.
    now = datetime.now(timezone.utc)
    rows = build_rows(df, args.site_id, now)

    print(f"  → {len(rows['visitors']):,} customers, "
          f"{len(rows['events']):,} site events, "
          f"{len(rows['interactions']):,} email interactions")

    _insert(rows, args.site_id)

    summary = db.fetch_one(
        """
        SELECT count(*) AS customers,
               count(*) FILTER (WHERE email_consent) AS contactable,
               count(*) FILTER (WHERE utm_source = 'email') AS from_email
        FROM visitors WHERE site_id = :s AND source = 'dataset'
        """, s=args.site_id)

    print(f"\n✓ Imported into '{site['name']}' (site {args.site_id})")
    print(f"  {summary['customers']:,} customers · "
          f"{summary['contactable']:,} opted in to email")
    print("\n  Every one is labelled source='dataset'. Their totals are real "
          "measurements;\n  the timing and ordering of their events is a "
          "reconstruction — see this file's\n  docstring, and /research on the "
          "dashboard.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
