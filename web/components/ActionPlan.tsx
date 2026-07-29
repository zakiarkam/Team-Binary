"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Card, Pill, SectionLabel } from "@/components/ui";

/**
 * The Action Plan — the thing a marketer actually works from.
 *
 * Every card is one job: what to do, who it is for, why, and the finished
 * content ready to copy. The platform never publishes; the company does.
 */

export interface PlanAction {
  kind: "email" | "post";
  priority: number;
  rationale: string | null;
  // email
  campaign_id?: number;
  step?: number;
  strategy?: string;
  subject?: string | null;
  body?: string | null;
  audience_size?: number;
  simulated_audience?: boolean;
  // post
  id?: number;
  platform?: string;
  caption?: string | null;
  hashtags?: string[];
  cta?: string | null;
  image_brief?: string | null;
  tracked_link?: string;
  status?: string;
}

const PLATFORM_LABEL: Record<string, string> = {
  email: "Email",
  instagram: "Instagram",
  linkedin: "LinkedIn",
  shorts: "Short video",
  facebook: "Facebook",
};

function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setDone(true);
        setTimeout(() => setDone(false), 1500);
      }}
      className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-bold
                 text-slate-700 hover:bg-slate-50"
    >
      {done ? "Copied ✓" : label}
    </button>
  );
}

function Done({
  onClick,
  busy,
}: {
  onClick: () => void;
  busy: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={busy}
      className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-bold text-white
                 hover:bg-slate-700 disabled:opacity-60"
    >
      {busy ? "Saving…" : "Mark as done"}
    </button>
  );
}

export function ActionPlan({ actions }: { actions: PlanAction[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);

  async function markDone(a: PlanAction) {
    const key = a.kind === "post" ? `p${a.id}` : `e${a.campaign_id}-${a.step}`;
    setBusy(key);
    const url =
      a.kind === "post"
        ? `/api/actions/posts/${a.id}/executed`
        : `/api/actions/emails/${a.campaign_id}/${a.step}/executed`;
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ executed: true }),
    });
    setBusy(null);
    router.refresh();
  }

  if (!actions.length) {
    return (
      <Card>
        <p className="text-sm text-slate-500">
          No outstanding actions. Generate a plan to get your next steps.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {actions.map((a) => {
        const key =
          a.kind === "post" ? `p${a.id}` : `e${a.campaign_id}-${a.step}`;
        const platform = a.kind === "email" ? "email" : a.platform ?? "";

        return (
          <Card key={key}>
            <div className="flex flex-wrap items-center gap-2">
              <Pill tone={a.kind === "email" ? "brand" : "accent"}>
                {PLATFORM_LABEL[platform] ?? platform}
              </Pill>
              {a.kind === "email" && (
                <span className="text-sm font-semibold text-slate-800">
                  Send to {a.audience_size} contact
                  {a.audience_size === 1 ? "" : "s"}
                </span>
              )}
              {a.kind === "post" && (
                <span className="text-sm font-semibold text-slate-800">
                  Publish this post
                </span>
              )}
              {a.simulated_audience && <Pill tone="warn">simulated audience</Pill>}
            </div>

            {a.rationale && (
              <p className="mt-2 text-sm leading-relaxed text-slate-600">
                {a.rationale}
              </p>
            )}

            {/* ── The content, ready to paste ── */}
            {a.kind === "email" ? (
              <div className="mt-3 rounded-xl border border-slate-200">
                <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2">
                  <span className="text-xs font-bold uppercase tracking-wide text-slate-400">
                    Subject
                  </span>
                  <CopyButton text={a.subject ?? ""} label="Copy subject" />
                </div>
                <p className="px-4 py-2 text-sm font-medium text-slate-800">
                  {a.subject}
                </p>
                <div className="flex items-center justify-between border-y border-slate-200 px-4 py-2">
                  <span className="text-xs font-bold uppercase tracking-wide text-slate-400">
                    Body
                  </span>
                  <CopyButton text={a.body ?? ""} label="Copy body" />
                </div>
                <pre className="max-h-56 overflow-auto whitespace-pre-wrap px-4 py-3 text-sm text-slate-700">
                  {a.body}
                </pre>
              </div>
            ) : (
              <div className="mt-3 rounded-xl border border-slate-200">
                <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2">
                  <span className="text-xs font-bold uppercase tracking-wide text-slate-400">
                    Caption
                  </span>
                  <CopyButton
                    text={[a.caption, (a.hashtags ?? []).join(" "), a.cta]
                      .filter(Boolean)
                      .join("\n\n")}
                    label="Copy post"
                  />
                </div>
                <p className="px-4 py-3 text-sm leading-relaxed text-slate-700">
                  {a.caption}
                </p>
                {!!(a.hashtags ?? []).length && (
                  <p className="px-4 pb-2 text-sm text-[#3b5bdb]">
                    {(a.hashtags ?? []).join(" ")}
                  </p>
                )}
                {a.cta && (
                  <p className="px-4 pb-3 text-sm font-semibold text-slate-800">
                    {a.cta}
                  </p>
                )}
                {a.image_brief && (
                  <div className="border-t border-slate-200 px-4 py-2">
                    <span className="text-xs font-bold uppercase tracking-wide text-slate-400">
                      Visual brief
                    </span>
                    <p className="text-sm text-slate-600">{a.image_brief}</p>
                  </div>
                )}
                {a.tracked_link && (
                  <div className="border-t border-slate-200 px-4 py-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wide text-slate-400">
                        Link to use
                      </span>
                      <CopyButton text={a.tracked_link} label="Copy link" />
                    </div>
                    <p className="break-all font-mono text-xs text-slate-600">
                      {a.tracked_link}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      Use this exact link. It records the click and tags the
                      visit with its platform — that is how a post you publish
                      yourself still shows up in your analytics.
                    </p>
                  </div>
                )}
              </div>
            )}

            <div className="mt-3 flex items-center gap-2">
              <Done onClick={() => markDone(a)} busy={busy === key} />
              <span className="text-xs text-slate-400">
                Mark it done once you have sent or published it.
              </span>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

export function GeneratePlanButton({ siteId }: { siteId: number }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [strategy, setStrategy] = useState("hybrid");

  async function run() {
    setBusy(true);
    await fetch(`/api/sites/${siteId}/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ strategy }),
    });
    setBusy(false);
    router.refresh();
  }

  return (
    <Card className="mb-4">
      <SectionLabel>PLAN MY NEXT MOVE</SectionLabel>
      <p className="mt-2 text-sm text-slate-600">
        Reads your audience, your analytics and your website, then writes the
        content and tells you what to do with it.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <select
          value={strategy}
          onChange={(e) => setStrategy(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800"
        >
          <option value="hybrid">Hybrid — segment-aware, behaviour-driven</option>
          <option value="trigger">Trigger — one message, then react</option>
          <option value="fixed">Fixed — the whole sequence upfront</option>
        </select>
        <button
          onClick={run}
          disabled={busy}
          className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-bold text-white
                     hover:bg-slate-700 disabled:opacity-60"
        >
          {busy ? "Planning…" : "Generate action plan"}
        </button>
      </div>
    </Card>
  );
}
