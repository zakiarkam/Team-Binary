/** Cookie names and lifetimes — one place, both sides of the handshake. */

export const SESSION_COOKIE = "mos_token";
export const SITE_COOKIE = "mos_site";

/** Matches SESSION_DAYS in api/auth.py. */
export const SESSION_MAX_AGE = 14 * 24 * 60 * 60;
