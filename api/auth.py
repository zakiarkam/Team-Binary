"""Accounts and sessions — the front door of the platform.

A company (the report's "User/Admin" in Figure 5.1) creates an account,
registers its website, and everything the system does is scoped to the sites
that account owns.

Design notes, chosen deliberately:

* **scrypt for passwords** (stdlib `hashlib.scrypt`). Memory-hard, no extra
  dependency, parameters stored alongside the hash so they can be raised later
  without invalidating existing users.
* **Opaque database-backed tokens**, not JWTs. A session is a ROW; logging out
  deletes it and the token is dead instantly. A JWT stays valid until expiry
  no matter what, which is the wrong trade-off for a dashboard.
* **Ownership, not roles.** A site either belongs to an account or it is
  unowned (created by local scripts/tests). Owned sites are invisible to every
  other account. Unowned sites remain reachable so the CLI demo pipeline and
  the test suite work without a login step.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException

from api import db

SESSION_DAYS = 14

# scrypt parameters — stored per-hash so future increases don't break old rows.
_N, _R, _P = 2**14, 8, 1


# ── Passwords ────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt_hex),
            n=int(n), r=int(r), p=int(p),
        )
        # Constant-time comparison — a plain == leaks timing information.
        return hmac.compare_digest(digest, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False


# ── Sessions ─────────────────────────────────────────────────────────────────

def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    db.execute(
        """
        INSERT INTO sessions (token, user_id, expires_at)
        VALUES (:token, :user_id, :expires_at)
        """,
        token=token,
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS),
    )
    return token


def destroy_session(token: str) -> None:
    db.execute("DELETE FROM sessions WHERE token = :token", token=token)


def user_for_token(token: str) -> dict | None:
    return db.fetch_one(
        """
        SELECT u.id, u.email, u.company_name
        FROM sessions s JOIN users u ON u.id = s.user_id
        WHERE s.token = :token AND s.expires_at > now()
        """,
        token=token,
    )


# ── FastAPI dependencies ─────────────────────────────────────────────────────

def optional_user(authorization: str | None = Header(default=None)) -> dict | None:
    """The logged-in account, or None for local/script access."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return user_for_token(authorization.removeprefix("Bearer ").strip())


def required_user(authorization: str | None = Header(default=None)) -> dict:
    user = optional_user(authorization)
    if user is None:
        raise HTTPException(401, "Sign in required")
    return user


def check_site_access(site_id: int, user: dict | None) -> None:
    """Enforce ownership on a site-scoped route.

    An owned site is its owner's alone — anyone else gets a 404, which does not
    even confirm that the site exists. An unowned site (created by local
    scripts or the test suite) stays open, so the CLI demo pipeline needs no
    login. What this rules out is the case that matters: one company reading
    another company's audience.
    """
    row = db.fetch_one("SELECT owner_id FROM sites WHERE id = :id", id=site_id)
    if row is None:
        raise HTTPException(404, "Site not found")
    if row["owner_id"] is not None and (user is None or user["id"] != row["owner_id"]):
        raise HTTPException(404, "Site not found")
