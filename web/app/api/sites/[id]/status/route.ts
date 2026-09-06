import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { API_URL } from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/session";

/** Has the snippet on this website sent us anything yet? */
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Sign in required" }, { status: 401 });
  }

  const { id } = await params;
  const res = await fetch(`${API_URL}/sites/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json({ detail: "Site not found" }, { status: res.status });
  }
  const data = await res.json();
  return NextResponse.json({
    events: data.stats?.events ?? 0,
    visitors: data.stats?.visitors ?? 0,
  });
}
