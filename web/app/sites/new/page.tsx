"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { CheckCircle2, Copy, Loader2 } from "lucide-react";

import { Button, Field } from "@/components/ui";

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

function StepCard({
  step,
  title,
  children,
}: {
  step: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card">
      <div className="flex items-center gap-3">
        <span
          className="grid h-7 w-7 shrink-0 place-items-center rounded-full
                         bg-brand-soft text-xs font-extrabold text-brand"
        >
          {step}
        </span>
        <h2 className="font-bold text-slate-800">{title}</h2>
      </div>
      <div className="mt-2 pl-10">{children}</div>
    </div>
  );
}

export default function NewSitePage() {
  const router = useRouter();
  const [created, setCreated] = useState<Created | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

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

  function copySnippet() {
    if (!created) return;
    navigator.clipboard.writeText(created.snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="mx-auto max-w-6xl">
      <p className="text-xs font-bold uppercase tracking-widest text-slate-400">
        Get started
      </p>
      <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-slate-900">
        Add your website
      </h1>
      <p className="mt-1 text-sm text-slate-500">
        Tell us where your product lives. Its visitors become the audience this
        system segments, emails and analyses.
      </p>

      {!created ? (
        <form onSubmit={submit} className="card mt-6">
          <div className="grid gap-4 lg:grid-cols-2">
            <Field
              label="Website name"
              name="name"
              placeholder="Aymex"
              required
            />
            <Field
              label="Website URL"
              name="url"
              type="url"
              placeholder="https://aymex.example"
              required
            />
            <Field
              label="Product name (optional)"
              name="product_name"
              placeholder="Aymex Analytics Suite"
            />
            <Field
              label="Target audience (optional)"
              name="target_audience"
              placeholder="Small business owners"
            />
            <div className="lg:col-span-2">
              <Field
                label="What does it do? (optional)"
                name="description"
                as="textarea"
                rows={3}
                placeholder="One or two sentences — used to seed generated marketing copy until the crawler has read your site."
              />
            </div>
          </div>
          {error && (
            <p className="mt-4 rounded-lg bg-bad-soft px-3 py-2 text-sm font-medium text-bad">
              {error}
            </p>
          )}
          <Button
            type="submit"
            size="lg"
            disabled={busy}
            className="mt-5 w-full"
          >
            {busy && <Loader2 size={15} className="animate-spin" />}
            {busy ? "Registering…" : "Register website"}
          </Button>
        </form>
      ) : (
        <div className="mt-6 space-y-4">
          <StepCard step="1" title="Paste this into your website's <head>">
            <p className="text-sm text-slate-500">
              One line. It collects page views, scrolls, clicks and purchases —
              first-party, honouring Do&nbsp;Not&nbsp;Track.
            </p>
            <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-800 p-4 text-xs text-emerald-300">
              {created.snippet}
            </pre>
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              onClick={copySnippet}
            >
              {copied ? (
                <CheckCircle2 size={13} className="text-ok" />
              ) : (
                <Copy size={13} />
              )}
              {copied ? "Copied" : "Copy snippet"}
            </Button>
          </StepCard>

          <StepCard step="2" title="Keep this secret safe">
            <p className="text-sm text-slate-500">
              Your server-to-server key. It is shown only once — store it like a
              password.
            </p>
            <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-100 p-3 text-xs text-slate-700">
              {created.ingest_secret}
            </pre>
          </StepCard>

          <StepCard step="3" title="Check the installation">
            <p className="text-sm text-slate-500">
              Once the snippet is live, open your website in another tab — the
              visit should arrive here within seconds.
            </p>
            {received === null ? (
              <Button
                className="mt-3"
                disabled={checking}
                onClick={checkInstallation}
              >
                {checking && <Loader2 size={14} className="animate-spin" />}
                {checking ? "Listening for events…" : "Check installation"}
              </Button>
            ) : received > 0 ? (
              <p
                className="mt-3 flex items-center gap-2 rounded-lg bg-ok-soft px-4
                            py-3 text-sm font-semibold text-green-700"
              >
                <CheckCircle2 size={16} />
                Receiving data — {received} event{received === 1 ? "" : "s"} so
                far.
              </p>
            ) : (
              <p className="mt-3 rounded-lg bg-warn-soft px-4 py-3 text-sm text-warn">
                Nothing yet. Make sure the snippet is deployed, then check again —
                or continue and come back later.
              </p>
            )}
          </StepCard>

          <Button
            size="lg"
            className="w-full"
            onClick={() => {
              router.push("/dashboard");
              router.refresh();
            }}
          >
            Go to dashboard →
          </Button>
        </div>
      )}
    </div>
  );
}
