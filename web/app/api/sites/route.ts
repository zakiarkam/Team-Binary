import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { API_URL } from "@/lib/api";
import { SESSION_COOKIE, SITE_COOKIE } from "@/lib/session";

/** Register a website for the signed-in company. */
export async function POST(req: Request) {
  const jar = await cookies();
  const token = jar.get(SESSION_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Sign in required" }, { status: 401 });
  }

  const body = await req.json().catch(() => null);
  if (!body?.name || !body?.url) {
    return NextResponse.json(
      { detail: "Website name and URL are required" },
      { status: 400 },
    );
  }

  const res = await fetch(`${API_URL}/sites`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      name: body.name,
      url: body.url,
      product_name: body.product_name || null,
      description: body.description || null,
      target_audience: body.target_audience || null,
    }),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof data?.detail === "string" ? data.detail : "Could not register the website";
    return NextResponse.json({ detail }, { status: res.status });
  }

  // The site just added becomes the selected one.
  jar.set(SITE_COOKIE, String(data.site.id), { path: "/", sameSite: "lax" });
  return NextResponse.json(data, { status: 201 });
}
