"""FastAPI backend for the AI-Powered Digital Marketing Orchestration system.

This is the "FastAPI Backend" box in Figure 5.1 of the report: the dashboard and
the client website's tracking snippet both talk to it, and it owns PostgreSQL
and drives the four AI modules.

Run:
    docker-compose up -d                        # PostgreSQL
    venv/bin/uvicorn api.main:app --reload      # this API  → http://localhost:8000/docs
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Module 4 keeps flat internal imports (`import config`, `import crawler`, …)
# from its own folder under modules/, so that folder joins the path first.
_M4_DIR = _Path(__file__).resolve().parents[1] / "modules" / "m4_content"
if str(_M4_DIR) not in _sys.path:
    _sys.path.insert(0, str(_M4_DIR))

# Loaded before anything numeric, on purpose. This process serves both Module 3
# (XGBoost) and Module 4 (PyTorch); on macOS their bundled OpenMP runtimes clash
# and the worker dies with a bare segfault mid-request — no traceback, no 500,
# just a dropped connection. See openmp_guard.py.
import openmp_guard  # noqa: F401  (import order matters)

import logging  # noqa: E402
import re  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
from pathlib import Path  # noqa: E402

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from api import auth as auth_svc
from api import db
from api.routers import (actions, analytics, auth, campaigns, collect,
                         content, research, segments, sites, tracking,
                         visitors)
from api.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("mos.api")

STATIC = Path(__file__).resolve().parent / "static"

# Routes the client's website calls cross-origin from any domain. They are
# append-only or read-nothing, so a wildcard origin is safe here — unlike the
# dashboard routes, which stay restricted to the configured origins.
PUBLIC_PATHS = ("/collect", "/mos.js", "/track/", "/unsubscribe", "/l/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    log.info("connecting to %s:%s/%s",
             settings.postgres_host, settings.postgres_port, settings.postgres_db)
    db.init_schema()
    log.info("schema applied")
    log.info("email delivery: %s",
             "LIVE via SMTP" if settings.email_enabled else "DRY-RUN (no SMTP configured)")
    yield


app = FastAPI(
    title="Marketing OS API",
    description=(
        "Backend for the AI-Powered Digital Marketing Orchestration framework — "
        "Team Binary, University of Moratuwa, 2026."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def allow_public_tracking_origins(request: Request, call_next):
    """The tracking snippet runs on the customer's domain, which we cannot know
    in advance. Allow any origin for the append-only tracking routes only."""
    response = await call_next(request)
    if request.url.path.startswith(PUBLIC_PATHS):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    return response


# ── Tenant isolation ─────────────────────────────────────────────────────────
# Every data route carries the site it belongs to, either directly in the path
# or one lookup away. Enforcing ownership HERE — not per-route — means a new
# endpoint cannot forget the check: if it is site-scoped, it is covered.
_SITE_PATH = re.compile(r"^/sites/(\d+)(?:/|$)")
_VISITOR_PATH = re.compile(r"^/visitors/(\d+)(?:/|$)")
_CAMPAIGN_PATH = re.compile(r"^/campaigns/(\d+)(?:/|$)")


def _site_for_path(path: str) -> int | None:
    if m := _SITE_PATH.match(path):
        return int(m.group(1))
    if m := _VISITOR_PATH.match(path):
        row = db.fetch_one("SELECT site_id FROM visitors WHERE id = :i", i=int(m.group(1)))
        return row["site_id"] if row else None
    if m := _CAMPAIGN_PATH.match(path):
        row = db.fetch_one("SELECT site_id FROM campaigns WHERE id = :i", i=int(m.group(1)))
        return row["site_id"] if row else None
    return None


@app.middleware("http")
async def enforce_site_ownership(request: Request, call_next):
    """A company's data is that company's alone.

    Owned sites answer only to their owner's token; unowned sites (created by
    local scripts and the test suite) stay open so the CLI pipeline needs no
    login. Denials are 404, not 403 — a rejected guess must not confirm that
    another tenant's site exists.
    """
    site_id = _site_for_path(request.url.path)
    if site_id is not None:
        user = None
        authz = request.headers.get("authorization", "")
        if authz.startswith("Bearer "):
            user = auth_svc.user_for_token(authz.removeprefix("Bearer ").strip())
        try:
            auth_svc.check_site_access(site_id, user)
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return await call_next(request)


app.include_router(auth.router)
app.include_router(sites.router)
app.include_router(collect.router)
app.include_router(visitors.router)
app.include_router(segments.router)
app.include_router(campaigns.router)
app.include_router(tracking.router)
app.include_router(analytics.router)
app.include_router(content.router)
app.include_router(actions.router)
app.include_router(research.router)


@app.get("/mos.js", include_in_schema=False)
def tracking_snippet() -> FileResponse:
    """Serve the tracker itself, so a client only ever needs one script tag."""
    return FileResponse(
        STATIC / "mos.js",
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.get("/health", tags=["system"])
def health() -> dict:
    """Liveness + database reachability, used by the dashboard and by CI."""
    settings = get_settings()
    db_ok = db.ping()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "up" if db_ok else "down",
        "email_delivery": "live" if settings.email_enabled else "dry_run",
        "version": app.version,
    }
