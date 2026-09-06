"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  BarChart3,
  ChevronDown,
  FlaskConical,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Megaphone,
  Menu,
  PenSquare,
  Plus,
  Search,
  Users,
  X,
} from "lucide-react";

import { NavLink } from "@/components/NavLink";
import type { Site, User } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/plan", label: "Action Plan", icon: ListChecks },
  { href: "/dashboard/audience", label: "Audience", icon: Users },
  { href: "/dashboard/campaigns", label: "Campaigns", icon: Megaphone },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/dashboard/content", label: "Content", icon: PenSquare },
  { href: "/dashboard/research", label: "Research", icon: FlaskConical },
];

/** Pages that provide their own full-screen layout (no sidebar or header). */
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
    <div className="px-2 pb-5">
      <p className="px-1 pb-1.5 text-[0.66rem] font-bold tracking-[0.14em] text-slate-400">
        WEBSITE
      </p>
      <select
        value={currentSiteId ?? undefined}
        onChange={(e) => choose(e.target.value)}
        className="w-full rounded-lg border border-white/15 bg-white/10 px-2.5 py-2
                   text-sm font-medium text-white transition hover:bg-white/15
                   [&>option]:text-slate-800"
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

/** Header avatar with a dropdown holding the account details and sign-out. */
function UserMenu({ user }: { user: User }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  async function signOut() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  const initial = (user.company_name || user.email || "?")
    .trim()
    .charAt(0)
    .toUpperCase();

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center gap-2 rounded-full py-1 pl-1 pr-2 transition
                   hover:bg-slate-100"
      >
        <span
          className="grid h-8 w-8 place-items-center rounded-full bg-brand
                         text-sm font-bold text-white"
        >
          {initial}
        </span>
        <span
          className="hidden max-w-40 truncate text-sm font-semibold
                         text-slate-700 md:block"
        >
          {user.company_name}
        </span>
        <ChevronDown size={14} className="text-slate-400" />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-2 w-64 overflow-hidden rounded-xl
                     border border-line bg-white shadow-lg"
        >
          <div className="border-b border-line px-4 py-3">
            <p className="truncate text-sm font-bold text-slate-800">
              {user.company_name}
            </p>
            <p className="truncate text-xs text-slate-500">{user.email}</p>
          </div>
          <button
            onClick={signOut}
            className="flex w-full items-center gap-2 px-4 py-2.5 text-sm
                       font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            <LogOut size={15} className="text-slate-400" />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

/** Global search  submits to the audience page, which filters server-side. */
function GlobalSearch() {
  return (
    <form
      action="/dashboard/audience"
      method="get"
      className="relative hidden flex-1 max-w-md sm:block"
    >
      <Search
        size={15}
        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
      />
      <input
        type="search"
        name="q"
        placeholder="Search visitors by email or ID…"
        aria-label="Search visitors"
        className="w-full rounded-full border border-slate-200 bg-slate-50 py-1.5
                   pl-9 pr-3 text-sm placeholder:text-slate-400 transition
                   focus:border-brand focus:bg-white"
      />
    </form>
  );
}

function Sidebar({
  sites,
  currentSiteId,
  onNavigate,
}: {
  sites: Site[];
  currentSiteId: number | null;
  onNavigate?: () => void;
}) {
  return (
    <div className="flex h-full flex-col bg-linear-to-b from-sidebar to-sidebar-deep px-4 py-6 text-slate-200">
      <Link
        href="/dashboard"
        onClick={onNavigate}
        className="flex items-center gap-2.5 px-2 pb-6"
      >
        <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand font-bold text-white shadow-md">
          M
        </span>
        <span className="text-sm font-extrabold tracking-widest text-white">
          MARKETING OS
        </span>
      </Link>

      {sites.length > 0 && (
        <SiteSwitcher sites={sites} currentSiteId={currentSiteId} />
      )}

      <p className="px-3 pb-2 text-[0.66rem] font-bold tracking-[0.14em] text-slate-400">
        MENU
      </p>
      {/* flex-1 + overflow keeps the account footer pinned to the bottom of the
          viewport, so nothing in the sidebar ever needs the page to scroll. */}
      <nav className="sidebar-scroll -mx-1 flex flex-1 flex-col gap-1 overflow-y-auto px-1">
        {NAV.map((item) => (
          <NavLink
            key={item.href}
            href={item.href}
            icon={item.icon}
            onNavigate={onNavigate}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-white/10 px-3 pt-4">
        <Link
          href="/sites/new"
          onClick={onNavigate}
          className="flex items-center gap-2 text-xs font-semibold text-slate-400
                     transition hover:text-white"
        >
          <Plus size={14} />
          Add another website
        </Link>
        <p className="mt-3 text-[0.7rem] leading-relaxed text-slate-500">
          Team Binary · UoM · 2026
        </p>
      </div>
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
  const [drawerOpen, setDrawerOpen] = useState(false);

  // The public landing (`/`), sign-in/up pages and the middleware's redirect
  // target render bare.
  if (pathname === "/" || BARE.some((p) => pathname.startsWith(p)) || !user) {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-screen">
      {/* Desktop sidebar: sticky and viewport-height, so it never scrolls away. */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 lg:block">
        <Sidebar sites={sites} currentSiteId={currentSiteId} />
      </aside>

      {/* Mobile drawer. */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-slate-900/50"
            onClick={() => setDrawerOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 w-72 shadow-2xl">
            <Sidebar
              sites={sites}
              currentSiteId={currentSiteId}
              onNavigate={() => setDrawerOpen(false)}
            />
          </aside>
          <button
            onClick={() => setDrawerOpen(false)}
            aria-label="Close menu"
            className="absolute right-4 top-4 grid h-9 w-9 place-items-center
                       rounded-full bg-white/90 text-slate-700 shadow"
          >
            <X size={18} />
          </button>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Header: hamburger (mobile), global search, account menu. */}
        <header
          className="sticky top-0 z-40 flex h-14 items-center gap-3 border-b
                           border-line bg-white/85 px-4 backdrop-blur lg:px-8"
        >
          <button
            onClick={() => setDrawerOpen(true)}
            aria-label="Open menu"
            className="grid h-9 w-9 place-items-center rounded-lg text-slate-600
                       transition hover:bg-slate-100 lg:hidden"
          >
            <Menu size={19} />
          </button>

          <GlobalSearch />

          <div className="flex-1" />

          <a
            href="http://localhost:4000"
            target="_blank"
            rel="noreferrer"
            className="hidden rounded-full border border-line px-3 py-1.5 text-xs
                       font-semibold text-slate-600 transition hover:bg-slate-50
                       md:block"
          >
            View demo store ↗
          </a>

          <UserMenu user={user} />
        </header>

        <main className="flex-1 px-4 py-6 lg:px-8 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
