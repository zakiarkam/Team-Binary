#!/usr/bin/env python
"""Run the Module 2 strategy comparison on a live audience.

Creates one campaign per automation policy — fixed, trigger, hybrid — over the
same audience, delivers the messages, and reports the funnel each one produced.
This is the live-data counterpart to Module 2's simulated comparison.

    venv/bin/python scripts/run_strategy_comparison.py --site-id 1
    venv/bin/python scripts/run_strategy_comparison.py --site-id 1 --reset

Honesty note
------------
Real recipients cannot be made to open an email on demand, so for demonstration
purposes this script can simulate recipient behaviour with `--simulate-engagement`.
Those events are recorded against synthetic visitors, so they land in the
database with `is_real = FALSE` and every report labels them `simulated`.
Without the flag, the funnel only ever fills from genuine human interaction.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

STRATEGIES = ("fixed", "trigger", "hybrid")

# Response rates used only when --simulate-engagement is passed.
P_OPEN, P_CLICK_GIVEN_OPEN, P_BUY_GIVEN_CLICK = 0.62, 0.45, 0.35


def _post(url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as res:
        raw = res.read()
        return json.loads(raw) if raw else {}


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as res:
        return json.loads(res.read())


def _hit(url: str) -> int:
    """Fetch a tracking URL the way a mail client would."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 MailClient"})
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return res.status
    except urllib.error.HTTPError as exc:
        return exc.code


def simulate_engagement(api: str, campaign_id: int, seed: int) -> dict:
    """Make simulated recipients behave like a plausible audience."""
    from api import db

    rng = random.Random(seed)
    sends = db.fetch_all(
        """
        SELECT s.track_token, v.visitor_uid, si.site_key
        FROM campaign_sends s
        JOIN visitors v  ON v.id = s.visitor_id
        JOIN sites    si ON si.id = v.site_id
        WHERE s.campaign_id = :c AND s.status IN ('sent', 'dry_run')
        """,
        c=campaign_id,
    )

    opens = clicks = buys = 0
    for send in sends:
        if rng.random() >= P_OPEN:
            continue
        _hit(f"{api}/track/open/{send['track_token']}.gif")
        opens += 1

        if rng.random() >= P_CLICK_GIVEN_OPEN:
            continue
        _hit(f"{api}/track/click/{send['track_token']}/0")
        clicks += 1

        if rng.random() >= P_BUY_GIVEN_CLICK:
            continue
        req = urllib.request.Request(
            f"{api}/collect", method="POST",
            data=json.dumps({
                "site_key": send["site_key"],
                "visitor_uid": send["visitor_uid"],
                "session_id": f"{send['visitor_uid']}-buy",
                "context": {"path": "/pricing.html", "device": "desktop"},
                "events": [{"type": "purchase", "path": "/pricing.html",
                            "props": {"plan": "growth", "value": 49}}],
            }).encode(),
            headers={"Content-Type": "text/plain"})
        urllib.request.urlopen(req, timeout=20).read()
        buys += 1

    return {"opens": opens, "clicks": clicks, "purchases": buys}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--site-id", type=int, default=1)
    ap.add_argument("--reset", action="store_true",
                    help="Delete this site's existing campaigns first")
    ap.add_argument("--simulate-engagement", action="store_true",
                    help="Simulate opens/clicks/purchases (recorded as is_real=FALSE)")
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()
    api = args.api.rstrip("/")

    from api import db

    if args.reset:
        db.execute("DELETE FROM campaigns WHERE site_id = :s", s=args.site_id)
        print(f"Cleared existing campaigns for site {args.site_id}")

    try:
        reach = _get(f"{api}/sites/{args.site_id}/audience/reachable")
    except urllib.error.URLError as exc:
        print(f"✗ Cannot reach the API at {api}\n  {exc}", file=sys.stderr)
        return 1

    print(f"\nAudience: {reach['visitors']} visitors · {reach['reachable']} contactable")
    print(f"  {reach['anonymous']} anonymous · {reach['known_no_consent']} known but "
          f"not opted in · {reach['unsubscribed']} unsubscribed")

    if reach["reachable"] == 0:
        print("\n✗ Nobody has opted in, so there is nobody to email.")
        print("  Generate demo traffic first:")
        print(f"    venv/bin/python scripts/generate_demo_traffic.py --site-id {args.site_id}")
        return 1

    created = []
    for strategy in STRATEGIES:
        camp = _post(f"{api}/sites/{args.site_id}/campaigns",
                     {"name": f"Launch sequence ({strategy})", "strategy": strategy})
        cid = camp["campaign_id"]
        created.append(cid)
        print(f"\n[{strategy}] campaign {cid}: {camp['recipients']} recipients, "
              f"{camp['scheduled_messages']} messages queued, "
              f"{camp['operational_complexity']} decision rules")

        result = _post(f"{api}/campaigns/{cid}/send?force=true&limit=500")
        print(f"[{strategy}] delivered {result['sent']} "
              f"({'DRY RUN' if result['dry_run'] else 'LIVE'})")

        if args.simulate_engagement:
            sim = simulate_engagement(api, cid, args.seed + cid)
            print(f"[{strategy}] simulated {sim['opens']} opens, "
                  f"{sim['clicks']} clicks, {sim['purchases']} purchases")
            follow = _post(f"{api}/campaigns/{cid}/advance")
            if follow.get("queued"):
                print(f"[{strategy}] queued {follow['queued']} behaviour-driven "
                      f"follow-ups {follow.get('breakdown', '')}")

    print("\n" + "=" * 86)
    print("STRATEGY COMPARISON" + ("  (simulated engagement)" if args.simulate_engagement
                                   else "  (real engagement only)"))
    print("=" * 86)
    header = (f"{'strategy':<9} {'recip':>6} {'sent':>5} {'open':>5} {'click':>6} "
              f"{'conv':>5} {'CTR':>7} {'conv/1k':>8} {'rules':>6}  basis")
    print(header)
    print("-" * 86)

    rows = _get(f"{api}/sites/{args.site_id}/campaigns")["campaigns"]
    for c in rows:
        if c["id"] not in created:
            continue
        print(f"{c['strategy']:<9} {c['recipients']:>6} {c['sent']:>5} {c['opens']:>5} "
              f"{c['clicks']:>6} {c['conversions']:>5} {c['click_through_rate']:>7.1%} "
              f"{c['conversions_per_1000_sends']:>8.1f} "
              f"{c['operational_complexity']:>6}  {c['data_basis']}")

    print("-" * 86)
    print("Open rate under-reports — most mail clients block the tracking pixel.")
    print("Operational complexity = number of distinct decision rules the policy needs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
