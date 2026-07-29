import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { API_URL } from "@/lib/api";
import { SESSION_COOKIE, SESSION_MAX_AGE } from "@/lib/session";

/**
 * The browser signs in against the dashboard's own origin; only this route
 * handler talks to the FastAPI backend. The token it gets back goes into an
 * HttpOnly cookie, which page JavaScript can never read — so a stray script
 * on the dashboard cannot exfiltrate a session.
 */
export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  if (!body?.email || !body?.password) {
    return NextResponse.json(
      { detail: "Email and password required" },
      { status: 400 },
    );
  }

  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: body.email, password: body.password }),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    return NextResponse.json(
      { detail: data?.detail ?? "Sign in failed" },
      { status: res.status },
    );
  }

  (await cookies()).set(SESSION_COOKIE, data.token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_MAX_AGE,
    // Behind HTTPS (any real deployment) the cookie must never travel over
    // plain HTTP. In local dev there is no TLS, so it stays off there.
    secure: process.env.NODE_ENV === "production",
  });
  return NextResponse.json({ user: data.user });
}
