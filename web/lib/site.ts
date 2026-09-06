import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { api, safeGet, type Health, type Site } from "@/lib/api";
import { SITE_COOKIE } from "@/lib/session";

/**
 * Resolve the site every dashboard page works against.
 *
 * The platform is multi-tenant: a signed-in company sees only its own sites
 * (the API enforces that). The switcher stores the chosen site id in a
 * cookie; anything stale or missing falls back to the company's first site.
 * A company with no site yet is sent to onboarding — there is nothing to
 * show until a website is registered.
 */
export async function currentSite(): Promise<{
  site: Site | null;
  health: Health | null;
  error: string | null;
}> {
  let health: Health | null = null;
  let sites: Site[] = [];
  try {
    [health, sites] = await Promise.all([
      api.get<Health>("/health"),
      api.get<Site[]>("/sites"),
    ]);
  } catch (err) {
    return {
      site: null,
      health: null,
      error: err instanceof Error ? err.message : "Unknown error",
    };
  }

  if (sites.length === 0) {
    // NOTE: outside the try/catch — redirect() works by throwing.
    redirect("/sites/new");
  }

  const selected = Number((await cookies()).get(SITE_COOKIE)?.value);
  const site = sites.find((s) => s.id === selected) ?? sites[0];
  return { site, health, error: null };
}

export { safeGet };
