"""Sites — register a client website and get its tracking snippet.

A "site" is the customer of this system: the website whose visitors become the
marketing audience. Registering one returns a public `site_key` (safe to embed
in the page) and a private `ingest_secret` (server-to-server only).
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from api import auth, db
from api.settings import get_settings

router = APIRouter(prefix="/sites", tags=["sites"])


class SiteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    url: HttpUrl
    product_name: str | None = None
    description: str | None = None
    target_audience: str | None = None


class Site(BaseModel):
    id: int
    site_key: str
    name: str
    url: str
    product_name: str | None = None
    description: str | None = None
    target_audience: str | None = None


def _snippet(site_key: str) -> str:
    """The one-line tag the client pastes into their website's <head>."""
    api = get_settings().public_api_url.rstrip("/")
    return f'<script defer src="{api}/mos.js" data-site="{site_key}"></script>'


@router.post("", response_model=dict, status_code=201)
def create_site(
    payload: SiteCreate,
    user: dict | None = Depends(auth.optional_user),
) -> dict:
    """Register a website. Returns the snippet to install on it.

    Registered through the app (with a login), the site belongs to that
    account. Created by a local script, it is unowned and open in local mode.
    """
    site_key = "mos_" + secrets.token_urlsafe(12)
    ingest_secret = secrets.token_urlsafe(32)

    row = db.fetch_one(
        """
        INSERT INTO sites (owner_id, site_key, ingest_secret, name, url,
                           product_name, description, target_audience)
        VALUES (:owner_id, :site_key, :ingest_secret, :name, :url,
                :product_name, :description, :target_audience)
        RETURNING id, site_key, name, url, product_name, description, target_audience
        """,
        owner_id=user["id"] if user else None,
        site_key=site_key,
        ingest_secret=ingest_secret,
        name=payload.name,
        url=str(payload.url),
        product_name=payload.product_name,
        description=payload.description,
        target_audience=payload.target_audience,
    )
    if row is None:  # pragma: no cover — INSERT ... RETURNING always yields a row
        raise HTTPException(500, "Failed to create site")

    return {
        "site": row,
        # Shown once, at creation time.
        "ingest_secret": ingest_secret,
        "snippet": _snippet(site_key),
    }


@router.get("", response_model=list[Site])
def list_sites(user: dict | None = Depends(auth.optional_user)) -> list[dict]:
    """The caller's sites.

    Signed in → the sites that account owns, and nothing else: one company
    must never see another company's websites. Unauthenticated (local scripts,
    tests) → the unowned sites only. Oldest first, so the default site is the
    one that was registered first, not whichever a test created last.
    """
    if user:
        return db.fetch_all(
            """
            SELECT id, site_key, name, url, product_name, description, target_audience
            FROM sites WHERE owner_id = :owner_id
            ORDER BY created_at ASC, id ASC
            """,
            owner_id=user["id"],
        )
    return db.fetch_all(
        """
        SELECT id, site_key, name, url, product_name, description, target_audience
        FROM sites WHERE owner_id IS NULL
        ORDER BY created_at ASC, id ASC
        """
    )


@router.get("/{site_id}", response_model=dict)
def get_site(site_id: int) -> dict:
    row = db.fetch_one(
        """
        SELECT id, site_key, name, url, product_name, description, target_audience,
               created_at
        FROM sites WHERE id = :site_id
        """,
        site_id=site_id,
    )
    if row is None:
        raise HTTPException(404, "Site not found")

    stats = db.fetch_one(
        """
        SELECT
          (SELECT count(*) FROM visitors WHERE site_id = :site_id)                     AS visitors,
          (SELECT count(*) FROM visitors WHERE site_id = :site_id AND email IS NOT NULL) AS known_visitors,
          (SELECT count(*) FROM visitors WHERE site_id = :site_id AND email_consent)   AS opted_in,
          (SELECT count(*) FROM events   WHERE site_id = :site_id)                     AS events
        """,
        site_id=site_id,
    )
    return {"site": row, "stats": stats, "snippet": _snippet(row["site_key"])}
