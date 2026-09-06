import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { SITE_COOKIE } from "@/lib/session";

/** Remember which of the company's sites the dashboard is showing. */
export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  const id = Number(body?.id);
  if (!Number.isInteger(id) || id <= 0) {
    return NextResponse.json({ detail: "A site id is required" }, { status: 400 });
  }
  (await cookies()).set(SITE_COOKIE, String(id), { path: "/", sameSite: "lax" });
  return NextResponse.json({ ok: true });
}
