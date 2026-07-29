"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

/** Shared shell for the sign-in and sign-up forms. */
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
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center justify-center gap-2">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-slate-800 font-bold text-white">
            M
          </div>
          <span className="text-sm font-extrabold tracking-widest text-slate-800">
            MARKETING OS
          </span>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <h1 className="text-xl font-extrabold text-slate-800">{title}</h1>
          <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
          <div className="mt-6">{children}</div>
        </div>
        <p className="mt-6 text-center text-xs text-slate-400">
          AI-Powered Digital Marketing Orchestration · Team Binary · UoM 2026
        </p>
      </div>
    </div>
  );
}

export function Field({
  label,
  ...props
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
        {label}
      </span>
      <input
        {...props}
        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm
                   text-slate-800 outline-none focus:border-slate-500"
      />
    </label>
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
    router.push("/");
    router.refresh();
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label="Email" name="email" type="email" autoComplete="email" required />
      <Field label="Password" name="password" type="password"
             autoComplete="current-password" required />
      {error && <p className="text-sm font-medium text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={busy}
        className="w-full rounded-lg bg-slate-800 py-2.5 text-sm font-bold text-white
                   hover:bg-slate-700 disabled:opacity-60"
      >
        {busy ? "Signing in…" : "Sign in"}
      </button>
      <p className="text-center text-sm text-slate-500">
        New here?{" "}
        <Link href="/signup" className="font-semibold text-slate-800 underline">
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
      <Field label="Company name" name="company_name" placeholder="Aymex"
             autoComplete="organization" required />
      <Field label="Work email" name="email" type="email"
             autoComplete="email" required />
      <Field label="Password" name="password" type="password" minLength={8}
             autoComplete="new-password" required
             placeholder="At least 8 characters" />
      {error && <p className="text-sm font-medium text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={busy}
        className="w-full rounded-lg bg-slate-800 py-2.5 text-sm font-bold text-white
                   hover:bg-slate-700 disabled:opacity-60"
      >
        {busy ? "Creating account…" : "Create account"}
      </button>
      <p className="text-center text-sm text-slate-500">
        Already registered?{" "}
        <Link href="/login" className="font-semibold text-slate-800 underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
