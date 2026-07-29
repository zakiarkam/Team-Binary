import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { API_URL } from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/session";

/**
 * Forward a dashboard action to the API with the session token attached.
 *
 * The token lives in an HttpOnly cookie that browser JavaScript cannot read,
 * so every client-initiated write goes through a route handler like this one.
 */
export async function forward(
  path: string,
  init: { method: string; body?: unknown } = { method: "POST" },
) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Sign in required" }, { status: 401 });
  }

  const res = await fetch(`${API_URL}${path}`, {
    method: init.method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
    cache: "no-store",
  });

  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
