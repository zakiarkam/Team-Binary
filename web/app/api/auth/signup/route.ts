import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { API_URL } from "@/lib/api";
import { SESSION_COOKIE, SESSION_MAX_AGE } from "@/lib/session";

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  if (!body?.email || !body?.password || !body?.company_name) {
    return NextResponse.json(
      { detail: "Company name, email and password are required" },
      { status: 400 },
    );
  }

  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: body.email,
      password: body.password,
      company_name: body.company_name,
    }),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof data?.detail === "string"
        ? data.detail
        : "Sign up failed — check the details and try again";
    return NextResponse.json({ detail }, { status: res.status });
  }

  // Signing up signs you in.
  (await cookies()).set(SESSION_COOKIE, data.token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_MAX_AGE,
    // Behind HTTPS (any real deployment) the cookie must never travel over
    // plain HTTP. In local dev there is no TLS, so it stays off there.
    secure: process.env.NODE_ENV === "production",
  });
  return NextResponse.json({ user: data.user }, { status: 201 });
}
