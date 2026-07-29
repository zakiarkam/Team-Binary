import { NextRequest, NextResponse } from "next/server";

import { SESSION_COOKIE } from "@/lib/session";

/**
 * Signed out → the sign-in page; signed in → keep them out of /login.
 *
 * This checks only that the cookie EXISTS — cheap enough to run on every
 * navigation. Whether the token is still valid is decided by the API on the
 * first data fetch; an expired session simply renders signed-out states and
 * the next navigation lands back here.
 */
const PUBLIC_PAGES = ["/login", "/signup"];

export function middleware(req: NextRequest) {
  const signedIn = req.cookies.has(SESSION_COOKIE);
  const { pathname } = req.nextUrl;
  const isPublic = PUBLIC_PAGES.some((p) => pathname.startsWith(p));

  if (!signedIn && !isPublic) {
    return NextResponse.redirect(new URL("/login", req.url));
  }
  if (signedIn && isPublic) {
    return NextResponse.redirect(new URL("/", req.url));
  }
  return NextResponse.next();
}

export const config = {
  // Everything except Next internals, static files, and the auth API routes
  // (which must work while signed out — that is how you sign in).
  matcher: ["/((?!_next/|api/auth/|favicon\\.ico|.*\\.(?:png|svg|ico|css|js)$).*)"],
};
