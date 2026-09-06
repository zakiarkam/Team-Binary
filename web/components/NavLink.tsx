"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";

/** Sidebar link that highlights the page you are on. */
export function NavLink({
  href,
  icon: Icon,
  onNavigate,
  children,
}: {
  href: string;
  icon?: LucideIcon;
  onNavigate?: () => void;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const active =
    href === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(href);

  return (
    <Link
      href={href}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-semibold transition ${
        active
          ? "bg-white text-brand shadow-sm"
          : "text-slate-300 hover:bg-white/10 hover:text-white"
      }`}
    >
      {Icon && (
        <Icon
          size={17}
          strokeWidth={2.2}
          className={active ? "text-brand" : "text-slate-400"}
        />
      )}
      {children}
    </Link>
  );
}
