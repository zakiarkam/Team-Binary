"""Sign up, sign in, sign out — a company's account on the platform."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field

from api import auth, db

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=200)


class Registration(Credentials):
    company_name: str = Field(..., min_length=1, max_length=200)


@router.post("/register", status_code=201)
def register(payload: Registration) -> dict:
    """Create a company account. Signing up also signs you in."""
    existing = db.fetch_one(
        "SELECT id FROM users WHERE lower(email) = lower(:email)",
        email=payload.email,
    )
    if existing:
        # 409, not 200-with-error: an account is a resource and it exists.
        raise HTTPException(409, "An account with this email already exists")

    user = db.fetch_one(
        """
        INSERT INTO users (email, password_hash, company_name)
        VALUES (lower(:email), :password_hash, :company_name)
        RETURNING id, email, company_name
        """,
        email=payload.email,
        password_hash=auth.hash_password(payload.password),
        company_name=payload.company_name,
    )
    return {"user": user, "token": auth.create_session(user["id"])}


@router.post("/login")
def login(payload: Credentials) -> dict:
    row = db.fetch_one(
        "SELECT id, email, company_name, password_hash FROM users "
        "WHERE lower(email) = lower(:email)",
        email=payload.email,
    )
    # One message for both failure modes, on purpose — "wrong password"
    # confirms the account exists, which is information an attacker wants.
    if row is None or not auth.verify_password(payload.password, row["password_hash"]):
        raise HTTPException(401, "Incorrect email or password")

    user = {k: row[k] for k in ("id", "email", "company_name")}
    return {"user": user, "token": auth.create_session(user["id"])}


@router.post("/logout")
def logout(authorization: str | None = Header(default=None)) -> dict:
    if authorization and authorization.startswith("Bearer "):
        auth.destroy_session(authorization.removeprefix("Bearer ").strip())
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(auth.required_user)) -> dict:
    return {"user": user}
