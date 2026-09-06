import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { cookies } from "next/headers";

import { AppShell } from "@/components/AppShell";
import { safeGet, type Site, type User } from "@/lib/api";
import { SITE_COOKIE } from "@/lib/session";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Marketing OS — AI Marketing Orchestration",
  description:
    "AI-Powered Digital Marketing Orchestration · Team Binary · University of Moratuwa 2026",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  // Who is signed in, and which of their sites is the dashboard showing?
  // Both resolve to null/empty on the sign-in pages — AppShell renders bare.
  const [me, sites] = await Promise.all([
    safeGet<{ user: User }>("/auth/me"),
    safeGet<Site[]>("/sites"),
  ]);

  const selected = Number((await cookies()).get(SITE_COOKIE)?.value);
  const siteList = sites ?? [];
  const currentSiteId =
    siteList.find((s) => s.id === selected)?.id ?? siteList[0]?.id ?? null;

  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen font-sans">
        <AppShell
          user={me?.user ?? null}
          sites={siteList}
          currentSiteId={currentSiteId}
        >
          {children}
        </AppShell>
      </body>
    </html>
  );
}
