"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { Field } from "@/components/AuthForm";

/**
 * Onboarding — a company registers its website and installs the snippet.
 *
 * This is the product's core promise made concrete: give us your website
 * link, paste one script tag into it, and the visitors of THAT website
 * become your marketing audience. Three steps, no jargon.
 */

interface Created {
  site: { id: number; name: string; site_key: string; url: string };
  snippet: string;
  ingest_secret: string;
}

export default function NewSitePage() {
  const router = useRouter();
  const [created, setCreated] = useState<Created | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Installation check state.
  const [checking, setChecking] = useState(false);
  const [received, setReceived] = useState<number | null>(null);
  const pollCount = useRef(0);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const form = new FormData(e.currentTarget);
    const res = await fetch("/api/sites", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: form.get("name"),
        url: form.get("url"),
        product_name: form.get("product_name"),
        description: form.get("description"),
        target_audience: form.get("target_audience"),
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(data?.detail ?? "Could not register the website");
      setBusy(false);
      return;
    }
    setCreated(data as Created);
    setBusy(false);
  }

  async function checkInstallation() {
    if (!created) return;
    setChecking(true);
    pollCount.current = 0;

    const poll = async (): Promise<void> => {
      pollCount.current += 1;
      const res = await fetch(`/api/sites/${created.site.id}/status`);
      const data = await res.json().catch(() => ({ events: 0 }));
      if (data.events > 0) {
        setReceived(data.events);
        setChecking(false);
        return;
      }
      if (pollCount.current >= 10) {
        setReceived(0);
        setChecking(false);
        return;
      }
      setTimeout(poll, 3000);
    };
    await poll();
  }

  return (
    <div className="mx-auto max-w-2xl py-4">
      <p className="text-xs font-bold uppercase tracking-widest text-slate-400">
        Get started
      </p>
      <h1 className="mt-1 text-2xl font-extrabold text-slate-800">
        Add your website
      </h1>
      <p className="mt-1 text-sm text-slate-500">
        Tell us where your product lives. Its visitors become the audience this
        system segments, emails and analyses.
      </p>

      {!created ? (
        <form
          onSubmit={submit}
          className="mt-6 space-y-4 rounded-2xl border border-slate-200 bg-white p-6"
        >
          <Field label="Website name" name="name" placeholder="Aymex" required />
          <Field label="Website URL" name="url" type="url"
                 placeholder="https://aymex.example" required />
          <Field label="Product name (optional)" name="product_name"
                 placeholder="Aymex Analytics Suite" />
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
              What does it do? (optional)
            </span>
            <textarea
              name="description"
              rows={3}
              placeholder="One or two sentences — used to seed generated marketing copy until the crawler has read your site."
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm
                         text-slate-800 outline-none focus:border-slate-500"
            />
          </label>
          <Field label="Target audience (optional)" name="target_audience"
                 placeholder="Small business owners" />
          {error && <p className="text-sm font-medium text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-slate-800 py-2.5 text-sm font-bold text-white
                       hover:bg-slate-700 disabled:opacity-60"
          >
            {busy ? "Registering…" : "Register website"}
          </button>
        </form>
      ) : (
        <div className="mt-6 space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-6">
            <h2 className="font-bold text-slate-800">
              1 · Paste this into your website&apos;s &lt;head&gt;
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              One line. It collects page views, scrolls, clicks and purchases —
              first-party, honouring Do&nbsp;Not&nbsp;Track.
            </p>
            <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-800 p-4 text-xs text-emerald-300">
              {created.snippet}
            </pre>
            <button
              onClick={() => navigator.clipboard.writeText(created.snippet)}
              className="mt-2 rounded-lg border border-slate-300 px-3 py-1.5 text-xs
                         font-bold text-slate-700 hover:bg-slate-50"
            >
              Copy snippet
            </button>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6">
            <h2 className="font-bold text-slate-800">2 · Keep this secret safe</h2>
            <p className="mt-1 text-sm text-slate-500">
              Your server-to-server key. It is shown only once — store it like a
              password.
            </p>
            <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-100 p-3 text-xs text-slate-700">
              {created.ingest_secret}
            </pre>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6">
            <h2 className="font-bold text-slate-800">3 · Check the installation</h2>
            <p className="mt-1 text-sm text-slate-500">
              Once the snippet is live, open your website in another tab — the
              visit should arrive here within seconds.
            </p>
            {received === null ? (
              <button
                onClick={checkInstallation}
                disabled={checking}
                className="mt-3 rounded-lg bg-slate-800 px-4 py-2 text-sm font-bold
                           text-white hover:bg-slate-700 disabled:opacity-60"
              >
                {checking ? "Listening for events…" : "Check installation"}
              </button>
            ) : received > 0 ? (
              <p className="mt-3 rounded-lg bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700">
                ✓ Receiving data — {received} event{received === 1 ? "" : "s"} so far.
              </p>
            ) : (
              <p className="mt-3 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
                Nothing yet. Make sure the snippet is deployed, then check again —
                or continue and come back later.
              </p>
            )}
          </div>

          <button
            onClick={() => {
              router.push("/");
              router.refresh();
            }}
            className="w-full rounded-lg bg-slate-800 py-2.5 text-sm font-bold text-white
                       hover:bg-slate-700"
          >
            Go to dashboard →
          </button>
        </div>
      )}
    </div>
  );
}
