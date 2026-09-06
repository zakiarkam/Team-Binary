#!/usr/bin/env python
"""Register the demo client website and install its tracking snippet.

Run once after the API is up:

    venv/bin/python scripts/setup_demo_site.py

Then serve the demo site on its own origin (so we exercise real cross-origin
tracking, exactly as a customer's website would):

    python3 -m http.server 4000 --directory demo-site

    demo site  → http://localhost:4000
    dashboard  → http://localhost:3000
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "demo-site"
PLACEHOLDER = "REPLACE_WITH_SITE_KEY"

DEMO_SITE = {
    "name": "Innov8Smart",
    "url": "http://localhost:4000",
    "product_name": "Innov8Smart",
    "description": (
        "Innov8Smart sells smart home and smart office devices that cut energy "
        "bills, secure your space and automate the small daily jobs. Free "
        "delivery over $75, a two-year warranty, and loyalty points on every "
        "order."
    ),
    "target_audience": "homeowners and small offices buying smart devices",
}


def _api(method: str, url: str, body: dict | None = None) -> dict | list:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--api", default="http://localhost:8000", help="API base URL")
    ap.add_argument("--force-new", action="store_true",
                    help="Register a new site even if one already exists")
    args = ap.parse_args()
    api = args.api.rstrip("/")

    # ── 1. Find or create the site ──────────────────────────────────────────
    try:
        existing = _api("GET", f"{api}/sites")
    except urllib.error.URLError as exc:
        print(f"✗ Cannot reach the API at {api} — is it running?\n  {exc}", file=sys.stderr)
        print("  Start it with:  venv/bin/uvicorn api.main:app --reload", file=sys.stderr)
        return 1

    assert isinstance(existing, list)
    match = next((s for s in existing if s["name"] == DEMO_SITE["name"]), None)

    if match and not args.force_new:
        site_key = match["site_key"]
        print(f"→ Reusing existing site '{DEMO_SITE['name']}' (id={match['id']})")
    else:
        created = _api("POST", f"{api}/sites", DEMO_SITE)
        assert isinstance(created, dict)
        site_key = created["site"]["site_key"]
        print(f"✓ Registered '{DEMO_SITE['name']}' (id={created['site']['id']})")

    # ── 2. Install the snippet into every demo page ─────────────────────────
    pattern = re.compile(r'(data-site=")([^"]*)(")')
    changed = 0
    for page in sorted(DEMO_DIR.glob("*.html")):
        html = page.read_text(encoding="utf-8")
        updated, n = pattern.subn(rf"\g<1>{site_key}\g<3>", html)
        # Point the snippet at whichever API host was given.
        updated = updated.replace("http://localhost:8000/mos.js", f"{api}/mos.js")
        if n and updated != html:
            page.write_text(updated, encoding="utf-8")
            changed += 1
        print(f"  · {page.name}: snippet → {site_key}")

    if changed:
        print(f"✓ Updated {changed} page(s)")

    # ── 3. Tell the user exactly what to do next ────────────────────────────
    print(
        f"""
Snippet now installed on the demo site:

    <script defer src="{api}/mos.js" data-site="{site_key}"></script>

Next:

  1. Serve the demo site on its own origin (new terminal):
         python3 -m http.server 4000 --directory demo-site

  2. Open http://localhost:4000 and browse around:
         · click links and buttons        → click events
         · scroll to the bottom           → scroll-depth events
         · submit the form with the box ticked → a known, contactable visitor
         · check out a basket on /cart.html → a purchase conversion

  3. Watch the audience fill up:
         curl -s {api}/sites/{{id}}/audience/summary | python3 -m json.tool
         or open the dashboard at http://localhost:3000
"""
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
