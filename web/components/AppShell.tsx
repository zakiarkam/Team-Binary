"use client";

import { usePathname, useRouter } from "next/navigation";

import { NavLink } from "@/components/NavLink";
import type { Site, User } from "@/lib/api";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/plan", label: "Action Plan" },
  { href: "/audience", label: "Audience" },
  { href: "/campaigns", label: "Campaigns" },
  { href: "/analytics", label: "Analytics" },
  { href: "/content", label: "Content" },
  { href: "/research", label: "Research" },
];

/** Pages that provide their own full-screen layout (no sidebar). */
const BARE = ["/login", "/signup"];

function SiteSwitcher({
  sites,
  currentSiteId,
}: {
  sites: Site[];
  currentSiteId: number | null;
}) {
  const router = useRouter();

  async function choose(value: string) {
    if (value === "__add__") {
      router.push("/sites/new");
      return;
    }
    await fetch("/api/sites/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: Number(value) }),
    });
    router.refresh();
  }

  return (
    <div className="px-2 pb-6">
      <p className="px-1 pb-1 text-[0.66rem] font-bold tracking-[0.14em] text-slate-400">
        WEBSITE
      </p>
      <select
        value={currentSiteId ?? undefined}
        onChange={(e) => choose(e.target.value)}
        className="w-full rounded-lg border border-white/20 bg-slate-700 px-2 py-1.5
                   text-sm text-white outline-none"
      >
        {sites.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
        <option value="__add__">＋ Add a website…</option>
      </select>
    </div>
  );
}

function AccountChip({ user }: { user: User }) {
  const router = useRouter();

  async function signOut() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="mt-10 border-t border-white/15 px-3 pt-3">
      <p className="truncate text-sm font-semibold text-white">{user.company_name}</p>
      <p className="truncate text-[0.7rem] text-slate-400">{user.email}</p>
      <button
        onClick={signOut}
        className="mt-2 w-full rounded-lg border border-white/20 py-1.5 text-xs
                   font-bold text-slate-200 hover:bg-white/10"
      >
        Sign out
      </button>
      <p className="mt-4 text-[0.7rem] leading-relaxed text-slate-400">
        Team Binary · UoM · 2026
      </p>
    </div>
  );
}

export function AppShell({
  user,
  sites,
  currentSiteId,
  children,
}: {
  user: User | null;
  sites: Site[];
  currentSiteId: number | null;
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  // Sign-in/up pages and the middleware's redirect target render bare.
  if (BARE.some((p) => pathname.startsWith(p)) || !user) {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col bg-slate-800 px-4 py-6 text-slate-200">
        <div className="flex items-center gap-2 px-2 pb-6">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-white/15 font-bold text-white">
            M
          </div>
          <span className="text-sm font-extrabold tracking-widest text-white">
            MARKETING OS
          </span>
        </div>

        {sites.length > 0 && (
          <SiteSwitcher sites={sites} currentSiteId={currentSiteId} />
        )}

        <p className="px-3 pb-2 text-[0.66rem] font-bold tracking-[0.14em] text-slate-400">
          MENU
        </p>
        <nav className="flex flex-col gap-1">
          {NAV.map((item) => (
            <NavLink key={item.href} href={item.href}>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex-1" />
        <AccountChip user={user} />
      </aside>

      <main className="flex-1 px-8 py-8">{children}</main>
    </div>
  );
}
