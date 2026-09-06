#!/usr/bin/env python
"""Build the complete research demonstration in one command.

Puts the whole study into a runnable state against a clean database:

    register the Innov8Smart store  →  install its tracking snippet
    import the 8,000-customer research dataset as that store's customers
    segment them                    (Module 1)
    read the store, generate content (Module 4)
    run all three automation policies (Module 2)
    analyse funnel, attribution, predictions (Module 3)
    build the Action Plan           →  what to send and post, content written

Nothing is emailed and nothing is published. The system advises; the company
executes.

    venv/bin/python scripts/build_research_demo.py              # full 8,000
    venv/bin/python scripts/build_research_demo.py --customers 1000
    venv/bin/python scripts/build_research_demo.py --keep-live  # keep live visitors

Prerequisites: PostgreSQL up, the API running, and the store served on :4000.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(ROOT / "modules" / "m4_content"))

PYTHON = str(ROOT / "venv" / "bin" / "python")

#: Recipients per campaign. Nearly every imported customer has opted in, and
#: the `fixed` policy commits five messages each — so the whole audience would
#: mean tens of thousands of drafts to demonstrate a difference that is already
#: clear at this size. The cap applies equally to all three policies, so the
#: comparison stays fair.
CAMPAIGN_LIMIT = 400


def step(n: int, total: int, title: str) -> None:
    print(f"\n\033[1m[{n}/{total}] {title}\033[0m")


def api_call(method: str, url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as res:
        raw = res.read()
        return json.loads(raw) if raw else {}


def run_script(name: str, *args: str) -> bool:
    proc = subprocess.run(
        [PYTHON, str(ROOT / "scripts" / name), *args],
        cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"   ✗ {name} failed:\n{proc.stdout[-800:]}{proc.stderr[-800:]}")
        return False
    for line in proc.stdout.strip().splitlines()[-4:]:
        if line.strip():
            print(f"   {line}")
    return True


def wait_for_api(api: str, timeout: int = 30) -> bool:
    for _ in range(timeout):
        try:
            urllib.request.urlopen(f"{api}/health", timeout=3).read()
            return True
        except Exception:
            time.sleep(1)
    return False


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--customers", type=int, default=None,
                    help="Import only the first N of the 8,000 (faster)")
    ap.add_argument("--keep-live", action="store_true",
                    help="Delete only imported customers, keeping live visitors")
    args = ap.parse_args()
    api = args.api.rstrip("/")

    print("\033[1mAI-Powered Digital Marketing Orchestration — research build\033[0m")

    if not wait_for_api(api):
        print(f"\n✗ The API is not responding at {api}.\n"
              "  Start it first:\n"
              "    docker-compose up -d\n"
              "    venv/bin/uvicorn api.main:app --reload --port 8000",
              file=sys.stderr)
        return 1

    from api import auth as auth_svc
    from api import db

    total = 9

    # ── 1. Clean slate ──────────────────────────────────────────────────────
    step(1, total, "Clearing previous build")
    if args.keep_live:
        db.execute("DELETE FROM visitors WHERE source = 'dataset'")
        print("   Removed imported customers; live visitors kept.")
    else:
        # Cascades to events, segments, campaigns, interactions and content.
        db.execute("DELETE FROM sites")
        print("   Removed all sites and everything belonging to them.")

    # ── 2. Register the store + install the snippet ─────────────────────────
    step(2, total, "Registering the Innov8Smart store and installing its snippet")
    if not run_script("setup_demo_site.py", "--api", api):
        return 1

    site = api_call("GET", f"{api}/sites")[0]
    site_id = site["id"]
    print(f"   site {site_id}: {site['name']} → {site['url']}")

    # The store is served locally, so point the crawler at that origin.
    db.execute("UPDATE sites SET url = :u WHERE id = :i",
               u="http://localhost:4000/index.html", i=site_id)

    # ── 3. The research audience ────────────────────────────────────────────
    step(3, total, "Importing the research dataset as the store's customers")
    import_args = ["--site-id", str(site_id)]
    if args.customers:
        import_args += ["--limit", str(args.customers)]
    if not run_script("import_research_audience.py", *import_args):
        return 1

    # ── 4. Segmentation ─────────────────────────────────────────────────────
    step(4, total, "Segmenting the audience (Module 1)")
    seg = api_call("POST", f"{api}/sites/{site_id}/segment")
    print(f"   mode: {seg['mode']} · {seg['n_visitors']:,} customers")
    for name, count in sorted(seg["segments"].items(), key=lambda kv: -kv[1]):
        print(f"     {name:<18} {count:>6,}")
    if seg.get("diagnostics", {}).get("silhouette") is not None:
        print(f"   silhouette: {seg['diagnostics']['silhouette']}")

    # ── 5. Content from the store's own pages ───────────────────────────────
    step(5, total, "Reading the store and generating content (Module 4)")
    try:
        content = api_call("POST", f"{api}/sites/{site_id}/content/generate",
                           {"engine": "fast"})
        print(f"   source: {content['content_source']} · "
              f"{content['n_assets']} assets · goal={content['campaign_goal']} "
              f"tone={content['tone']}")
        if content.get("site_keywords"):
            print(f"   keywords from the store: {', '.join(content['site_keywords'][:6])}")
    except urllib.error.HTTPError as exc:
        print(f"   ! content generation failed ({exc.code}) — is the store "
              "served on :4000? Continuing.")

    # ── 6. Campaigns ────────────────────────────────────────────────────────
    step(6, total, "Running all three automation policies (Module 2)")
    if not run_script("run_strategy_comparison.py", "--api", api,
                      "--site-id", str(site_id), "--reset", "--respond",
                      "--limit", str(CAMPAIGN_LIMIT)):
        return 1

    # ── 7. Analytics ────────────────────────────────────────────────────────
    step(7, total, "Analysing funnel, attribution and predictions (Module 3)")
    analytics = api_call("POST", f"{api}/sites/{site_id}/analytics/run")
    funnel = analytics["funnel"]["funnel"]
    print(f"   funnel: sent {funnel['sent']} → open {funnel['open']} → "
          f"click {funnel['click']} → convert {funnel['convert']} "
          f"[{analytics['funnel']['data_basis']}]")
    print(f"   {analytics['predictions']['n_users']:,} customers scored")
    print("\n   Findings:")
    for insight in analytics["insights"]:
        print(f"     · {insight}")

    # ── 8. The Action Plan ──────────────────────────────────────────────────
    step(8, total, "Building the Action Plan (what to send and post)")
    plan = api_call("POST", f"{api}/sites/{site_id}/plan",
                    {"strategy": "hybrid", "limit": CAMPAIGN_LIMIT})
    print(f"   {plan['email_actions']} email actions · "
          f"{plan['reachable']:,} contactable customers · "
          f"{plan['post_actions']} posts to publish")
    outstanding = api_call("GET", f"{api}/sites/{site_id}/plan")
    for action in outstanding["actions"][:4]:
        if action["kind"] == "email":
            print(f"     · EMAIL  \"{action['subject']}\" → "
                  f"{action['audience_size']} people")
        else:
            print(f"     · {action['platform'].upper():<10} {action['rationale'][:64]}")
    print("   Nothing was sent. These are recommendations with the content written.")

    # ── 9. The demo login ───────────────────────────────────────────────────
    # Ownership is assigned LAST, on purpose — the pipeline steps above call the
    # API without a token, and an owned site would (correctly) refuse them.
    step(9, total, "Creating the demo company account")
    demo_email = "demo@innov8smart.example"
    demo_password = "demo1234"
    user = db.fetch_one("SELECT id FROM users WHERE email = :e", e=demo_email)
    if user is None:
        user = db.fetch_one(
            """
            INSERT INTO users (email, password_hash, company_name)
            VALUES (:e, :p, 'Innov8Smart') RETURNING id
            """,
            e=demo_email, p=auth_svc.hash_password(demo_password),
        )
    db.execute("UPDATE sites SET owner_id = :o WHERE id = :i",
               o=user["id"], i=site_id)
    print(f"   {demo_email} owns site {site_id} — other accounts cannot see it")

    print(f"""
\033[1m✓ Ready.\033[0m

    Dashboard    http://localhost:3000/plan   ← start here: the Action Plan
                   sign in as  {demo_email}  /  {demo_password}
    Store        http://localhost:4000
    API docs     {api}/docs

Every customer above came from the published research dataset and is labelled
`source = 'dataset'`, so the dashboard reports these figures as research data
rather than as observed live behaviour. Browse the store yourself to add a
live visitor and watch the badge change to `dataset + live`.

Next: `make research` reproduces every experiment and figure in the report.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
