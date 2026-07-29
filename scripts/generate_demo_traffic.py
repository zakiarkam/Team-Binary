#!/usr/bin/env python
"""Generate simulated website traffic for demos and testing.

Why this exists
---------------
A brand-new product has no audience, which makes it hard to *show* what the
system does. This script posts realistic visitor sessions to the same public
`/collect` endpoint the real tracker uses — so nothing is faked at the database
layer, only the browsing is simulated.

Every visitor it creates is marked `is_synthetic = TRUE` in the database. That
flag is what keeps the demo honest: simulated visitors can be shown, counted and
segmented, but they can always be told apart from real ones, and they can be
deleted in a single command.

    venv/bin/python scripts/generate_demo_traffic.py --site-id 1 --visitors 120
    venv/bin/python scripts/generate_demo_traffic.py --site-id 1 --clear
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

# ── Visitor archetypes ───────────────────────────────────────────────────────
# Deliberately overlapping, not cleanly separated: real audiences do not come
# pre-clustered, and a segmentation engine that only works on tidy synthetic
# blobs would prove nothing.
ARCHETYPES = [
    {
        "name": "bouncer",          # lands, leaves — the cold-start majority
        "weight": 0.34,
        "sessions": (1, 1), "pages": (1, 1), "clicks": (0, 0),
        "depth": (10, 40), "seconds": (2, 15), "converts": 0.0, "identifies": 0.0,
    },
    {
        "name": "browser",          # reads a bit, does not commit
        "weight": 0.26,
        "sessions": (1, 2), "pages": (2, 4), "clicks": (0, 1),
        "depth": (40, 80), "seconds": (20, 90), "converts": 0.02, "identifies": 0.08,
    },
    {
        "name": "researcher",       # repeat visits, mostly pricing, low clicking
        "weight": 0.18,
        "sessions": (2, 4), "pages": (3, 7), "clicks": (0, 1),
        "depth": (50, 95), "seconds": (60, 240), "converts": 0.06, "identifies": 0.25,
    },
    {
        "name": "engaged",          # deep engagement, clicks a lot
        "weight": 0.14,
        "sessions": (1, 3), "pages": (3, 8), "clicks": (2, 6),
        "depth": (70, 100), "seconds": (90, 400), "converts": 0.28, "identifies": 0.55,
    },
    {
        "name": "customer",         # converts, and comes back
        "weight": 0.08,
        "sessions": (2, 5), "pages": (4, 10), "clicks": (3, 9),
        "depth": (80, 100), "seconds": (150, 600), "converts": 0.92, "identifies": 0.85,
    },
]

PAGES = ["/index.html", "/pricing.html", "/index.html#features"]
SOURCES = [
    ("linkedin", "social", "launch"), ("google", "cpc", "brand"),
    ("instagram", "social", "launch"), (None, None, None),   # direct
    ("newsletter", "email", "weekly"),
]
DEVICES = ["desktop", "desktop", "desktop", "mobile", "mobile", "tablet"]
FIRST = ["priya", "arjun", "nimal", "fatima", "dilan", "sanduni", "kasun", "aisha",
         "ravi", "tharindu", "menaka", "isuru", "hasini", "chamath", "nadia"]
LAST = ["perera", "silva", "fernando", "jayasuriya", "rahman", "wickrama",
        "gunasekara", "mendis", "bandara", "ismail"]


def _pick_archetype(rng: random.Random) -> dict:
    return rng.choices(ARCHETYPES, weights=[a["weight"] for a in ARCHETYPES])[0]


def _rng_int(rng: random.Random, span: tuple[int, int]) -> int:
    return rng.randint(*span)


def _build_session(rng: random.Random, arch: dict, page_budget: int,
                   started: datetime) -> list[dict]:
    """One browsing session as a list of tracker events."""
    events: list[dict] = []
    clock = started

    def add(kind: str, path: str, props: dict | None = None) -> None:
        nonlocal clock
        clock += timedelta(seconds=rng.randint(2, 40))
        events.append({"type": kind, "path": path, "props": props or {},
                       "ts": clock.isoformat()})

    for _ in range(page_budget):
        path = rng.choice(PAGES)
        add("page_view", path, {"title": "Innov8Smart"})

        depth = _rng_int(rng, arch["depth"])
        for mark in (25, 50, 75, 100):
            if depth >= mark:
                add("scroll", path, {"depth": mark})

        for _ in range(rng.randint(0, max(0, arch["clicks"][1] // 2))):
            add("click", path, {"label": rng.choice(
                ["hero_cta_start_free", "nav_cta_get_started", "plan_growth"])})

        add("page_exit", path,
            {"seconds": max(1, _rng_int(rng, arch["seconds"]) // page_budget)})

    return events


def _post(api: str, payload: dict) -> None:
    req = urllib.request.Request(
        f"{api}/collect", data=json.dumps(payload).encode(),
        method="POST", headers={"Content-Type": "text/plain"},
    )
    with urllib.request.urlopen(req, timeout=20) as res:
        if res.status not in (200, 204):
            raise RuntimeError(f"collect returned {res.status}")


def generate(api: str, site_key: str, count: int, days: int, seed: int) -> dict:
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    stats = {"visitors": 0, "events": 0, "identified": 0, "converted": 0}
    uids: list[str] = []

    for _ in range(count):
        arch = _pick_archetype(rng)
        uid = f"demo-{uuid.uuid4()}"
        uids.append(uid)

        source, medium, campaign = rng.choice(SOURCES)
        device = rng.choice(DEVICES)
        first_seen = now - timedelta(days=rng.uniform(0, days))

        n_sessions = _rng_int(rng, arch["sessions"])
        total_pages = max(1, _rng_int(rng, arch["pages"]))
        per_session = max(1, total_pages // n_sessions)

        converted = rng.random() < arch["converts"]
        identified = rng.random() < arch["identifies"]

        for s in range(n_sessions):
            started = first_seen + timedelta(days=s * rng.uniform(0.5, 3.0))
            if started > now:
                started = now - timedelta(minutes=rng.randint(1, 120))

            events = _build_session(rng, arch, per_session, started)

            # Identify and convert on the final session, as in real journeys.
            if s == n_sessions - 1:
                if identified:
                    name = f"{rng.choice(FIRST)}.{rng.choice(LAST)}"
                    events.append({
                        "type": "form_submit", "path": "/index.html",
                        "props": {"form": "demo_request"},
                        "ts": (started + timedelta(minutes=3)).isoformat()})
                    events.append({
                        "type": "identify", "path": "/index.html",
                        "props": {
                            "email": f"{name}@example.com",
                            "name": name.replace(".", " ").title(),
                            # Not everyone who leaves an email opts in — the gap
                            # between "known" and "contactable" is the point.
                            "consent": rng.random() < 0.72,
                            "source": "demo_request",
                        },
                        "ts": (started + timedelta(minutes=3, seconds=5)).isoformat()})
                    stats["identified"] += 1

                if converted:
                    plan = rng.choice(["starter", "growth", "growth", "scale"])
                    events.append({
                        "type": "purchase", "path": "/pricing.html",
                        "props": {"plan": plan,
                                  "value": {"starter": 0, "growth": 49, "scale": 149}[plan]},
                        "ts": (started + timedelta(minutes=6)).isoformat()})
                    stats["converted"] += 1

            # The endpoint caps a batch at 50 events.
            for i in range(0, len(events), 40):
                _post(api, {
                    "site_key": site_key,
                    "visitor_uid": uid,
                    "session_id": f"{uid}-s{s}",
                    "context": {
                        "path": "/index.html", "referrer": None, "device": device,
                        "utm_source": source, "utm_medium": medium,
                        "utm_campaign": campaign,
                    },
                    "events": events[i:i + 40],
                })
            stats["events"] += len(events)

        stats["visitors"] += 1

    return {**stats, "uids": uids}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--site-id", type=int, default=1)
    ap.add_argument("--visitors", type=int, default=120)
    ap.add_argument("--days", type=int, default=14, help="Spread traffic over N days")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--clear", action="store_true",
                    help="Delete all synthetic visitors for this site and exit")
    args = ap.parse_args()
    api = args.api.rstrip("/")

    # --clear talks to the database directly; everything else uses the public API.
    if args.clear:
        sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
        from api import db
        before = db.fetch_one(
            "SELECT count(*) n FROM visitors WHERE site_id=:s AND is_synthetic",
            s=args.site_id)["n"]
        db.execute("DELETE FROM visitors WHERE site_id=:s AND is_synthetic",
                   s=args.site_id)
        print(f"✓ Removed {before} synthetic visitors from site {args.site_id}. "
              "Real visitors were left untouched.")
        return 0

    try:
        with urllib.request.urlopen(f"{api}/sites/{args.site_id}", timeout=15) as res:
            site = json.loads(res.read().decode())["site"]
    except urllib.error.URLError as exc:
        print(f"✗ Cannot reach the API at {api} — is it running?\n  {exc}", file=sys.stderr)
        return 1

    print(f"Generating {args.visitors} simulated visitors for "
          f"'{site['name']}' over the last {args.days} days…")

    result = generate(api, site["site_key"], args.visitors, args.days, args.seed)

    # Mark them, so no synthetic visitor is ever mistaken for a real one.
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
    from api import db
    db.execute(
        "UPDATE visitors SET is_synthetic = TRUE "
        "WHERE site_id = :s AND visitor_uid LIKE 'demo-%'",
        s=args.site_id,
    )

    print(f"""
✓ {result['visitors']} visitors · {result['events']} events
  {result['identified']} left an email · {result['converted']} converted

  All are flagged is_synthetic = TRUE. Remove them any time with:
      venv/bin/python scripts/generate_demo_traffic.py --site-id {args.site_id} --clear

Now segment them:
      curl -X POST {api}/sites/{args.site_id}/segment | python3 -m json.tool
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
