"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/** Sidebar link that highlights the page you are on. */
export function NavLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const active = href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <Link
      href={href}
      className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${
        active
          ? "bg-white text-[#3b5bdb]"
          : "text-slate-200 hover:bg-white/10"
      }`}
    >
      {children}
    </Link>
  );
}
