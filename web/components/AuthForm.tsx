"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { BarChart3, Loader2, Megaphone, PenSquare, Users } from "lucide-react";

import { Button, Field } from "@/components/ui";

const MODULES = [
  {
    icon: Users,
    text: "Segment your audience with hybrid rule + ML intelligence",
  },
  {
    icon: Megaphone,
    text: "Run fixed, trigger-based and hybrid campaign policies",
  },
  { icon: BarChart3, text: "See funnels, attribution and next-best actions" },
  {
    icon: PenSquare,
    text: "Generate platform-ready content from your website",
  },
];

/** Shared split-screen shell for the sign-in and sign-up forms. */
export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-white">
      {/* Brand panel */}
      <aside
        className="relative hidden w-[44%] flex-col justify-between overflow-hidden
                        bg-linear-to-b from-sidebar to-sidebar-deep p-10 text-white lg:flex"
      >
        <div
          aria-hidden
          className="pointer-events-none absolute -right-28 -top-28 h-80 w-80
                     rounded-full bg-brand/30 blur-3xl"
        />
        <Link href="/" className="relative flex items-center gap-2.5">
          <span
            className="grid h-9 w-9 place-items-center rounded-xl bg-brand
                           font-bold text-white shadow-md"
          >
            M
          </span>
          <span className="text-sm font-extrabold tracking-widest">
            MARKETING OS
          </span>
        </Link>

        <div className="relative">
          <h2 className="max-w-sm text-3xl font-extrabold leading-tight tracking-tight">
            One closed loop for launch-stage marketing.
          </h2>
          <ul className="mt-8 space-y-4">
            {MODULES.map((m) => (
              <li
                key={m.text}
                className="flex items-start gap-3 text-sm text-slate-300"
              >
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-white/10">
                  <m.icon size={15} className="text-white" />
                </span>
                <span className="pt-1.5">{m.text}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-slate-500">
          AI-Powered Digital Marketing Orchestration · Team Binary · UoM 2026
        </p>
      </aside>

      {/* Form panel */}
      <main className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-md">
          <Link
            href="/"
            className="mb-6 flex items-center justify-center gap-2 lg:hidden"
          >
            <span
              className="grid h-10 w-10 place-items-center rounded-xl bg-brand
                             font-bold text-white"
            >
              M
            </span>
            <span className="text-sm font-extrabold tracking-widest text-slate-800">
              MARKETING OS
            </span>
          </Link>

          <div className="rounded-2xl border border-line bg-white p-8 shadow-sm">
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">
              {title}
            </h1>
            <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
            <div className="mt-6">{children}</div>
          </div>

          <p className="mt-6 text-center text-xs text-slate-400">
            <Link href="/" className="transition hover:text-slate-600">
              ← Back to overview
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const form = new FormData(e.currentTarget);
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: form.get("email"),
        password: form.get("password"),
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setError(body?.detail ?? "Sign in failed");
      setBusy(false);
      return;
    }
    router.push("/dashboard");
    router.refresh();
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Field
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        placeholder="you@company.com"
        required
      />
      <Field
        label="Password"
        name="password"
        type="password"
        autoComplete="current-password"
        placeholder="••••••••"
        required
      />
      {error && (
        <p className="rounded-lg bg-bad-soft px-3 py-2 text-sm font-medium text-bad">
          {error}
        </p>
      )}
      <Button type="submit" size="lg" disabled={busy} className="w-full">
        {busy && <Loader2 size={15} className="animate-spin" />}
        {busy ? "Signing in…" : "Sign in"}
      </Button>
      <p className="text-center text-sm text-slate-500">
        New here?{" "}
        <Link
          href="/signup"
          className="font-semibold text-brand hover:underline"
        >
          Create your company account
        </Link>
      </p>
    </form>
  );
}

export function SignupForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const form = new FormData(e.currentTarget);
    const res = await fetch("/api/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company_name: form.get("company_name"),
        email: form.get("email"),
        password: form.get("password"),
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setError(body?.detail ?? "Sign up failed");
      setBusy(false);
      return;
    }
    // A brand-new account has no website yet — take them straight to adding one.
    router.push("/sites/new");
    router.refresh();
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Field
        label="Company name"
        name="company_name"
        placeholder="Aymex"
        autoComplete="organization"
        required
      />
      <Field
        label="Work email"
        name="email"
        type="email"
        placeholder="you@company.com"
        autoComplete="email"
        required
      />
      <Field
        label="Password"
        name="password"
        type="password"
        minLength={8}
        autoComplete="new-password"
        required
        placeholder="At least 8 characters"
      />
      {error && (
        <p className="rounded-lg bg-bad-soft px-3 py-2 text-sm font-medium text-bad">
          {error}
        </p>
      )}
      <Button type="submit" size="lg" disabled={busy} className="w-full">
        {busy && <Loader2 size={15} className="animate-spin" />}
        {busy ? "Creating account…" : "Create account"}
      </Button>
      <p className="text-center text-sm text-slate-500">
        Already registered?{" "}
        <Link
          href="/login"
          className="font-semibold text-brand hover:underline"
        >
          Sign in
        </Link>
      </p>
    </form>
  );
}
