"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Loader2,
  Mail,
  Megaphone,
  Users,
} from "lucide-react";

import { Card, Pill, SectionLabel } from "@/components/ui";

/**
 * The Action Plan — the thing a marketer actually works from.
 *
 * Every card is one job: what to do, who it is for, why, and the finished
 * content ready to copy. The platform never publishes; the company does.
 * Actions are grouped into an Email tab and a Posts tab (with one sub-tab per
 * platform), so the marketer works through one channel at a time.
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
  dataset_audience?: boolean;
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

interface Recipient {
  name: string | null;
  email: string | null;
  segment: string | null;
  status: string | null;
}

const PLATFORM_LABEL: Record<string, string> = {
  email: "Email",
  instagram: "Instagram",
  linkedin: "LinkedIn",
  shorts: "Short video",
  tiktok: "TikTok",
  facebook: "Facebook",
};

const platformLabel = (p: string) =>
  PLATFORM_LABEL[p] ?? p.charAt(0).toUpperCase() + p.slice(1);

function CopyButton({
  text,
  label = "Copy",
}: {
  text: string;
  label?: string;
}) {
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

function Done({ onClick, busy }: { onClick: () => void; busy: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={busy}
      className="rounded-lg bg-brand px-3 py-1.5 text-xs font-bold text-white
                 transition hover:bg-brand-strong disabled:opacity-60"
    >
      {busy ? "Saving…" : "Mark as done"}
    </button>
  );
}

/**
 * The audience of one email action, spelled out.
 *
 * "Send to 194 contacts" is not verifiable; this fetches the actual list —
 * name, email address and segment — the first time it is opened.
 */
function RecipientList({
  campaignId,
  step,
  total,
}: {
  campaignId?: number;
  step?: number;
  total?: number;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState<Recipient[] | null>(null);

  async function toggle() {
    if (!open && rows === null) {
      setLoading(true);
      const res = await fetch(
        `/api/actions/emails/${campaignId}/${step}/recipients`,
      );
      const data = await res.json().catch(() => ({ recipients: [] }));
      setRows(data.recipients ?? []);
      setLoading(false);
    }
    setOpen((v) => !v);
  }

  return (
    <div className="mt-3">
      <button
        onClick={toggle}
        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300
                   px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50"
      >
        {loading ? (
          <Loader2 size={13} className="animate-spin" />
        ) : (
          <Users size={13} />
        )}
        {open ? "Hide recipients" : `View recipients (${total ?? "…"})`}
        {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>

      {open && rows && (
        <div className="mt-2 overflow-hidden rounded-xl border border-slate-200">
          <div className="max-h-64 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-50">
                <tr className="text-left">
                  <th className="px-3 py-2 text-xs font-bold uppercase tracking-wide text-slate-400">
                    Name
                  </th>
                  <th className="px-3 py-2 text-xs font-bold uppercase tracking-wide text-slate-400">
                    Email
                  </th>
                  <th className="px-3 py-2 text-xs font-bold uppercase tracking-wide text-slate-400">
                    Segment
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr
                    key={`${r.email ?? "anon"}-${i}`}
                    className="border-t border-slate-100"
                  >
                    <td className="px-3 py-1.5 text-slate-700">
                      {r.name || "—"}
                    </td>
                    <td className="px-3 py-1.5 font-mono text-xs text-slate-600">
                      {r.email || "—"}
                    </td>
                    <td className="px-3 py-1.5">
                      {r.segment ? (
                        <span className="rounded-full bg-brand-soft px-2 py-0.5 text-xs font-semibold text-brand">
                          {r.segment}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-3 py-3 text-sm text-slate-400">
                      No recipients found for this step.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {total != null && rows.length < total && (
            <p className="border-t border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-500">
              Showing the first {rows.length.toLocaleString()} of{" "}
              {total.toLocaleString()} recipients.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function ActionCard({
  a,
  index,
  busyKey,
  onDone,
}: {
  a: PlanAction;
  index: number;
  busyKey: string | null;
  onDone: (a: PlanAction) => void;
}) {
  const key = a.kind === "post" ? `p${a.id}` : `e${a.campaign_id}-${a.step}`;
  const platform = a.kind === "email" ? "email" : (a.platform ?? "");

  return (
    // The busy/done key can repeat (two email actions may share a campaign
    // and step), so the React key adds the position.
    <Card key={`${key}-${index}`}>
      <div className="flex flex-wrap items-center gap-2">
        <Pill tone={a.kind === "email" ? "brand" : "accent"}>
          {platformLabel(platform)}
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
        {a.dataset_audience && <Pill tone="muted">research audience</Pill>}
      </div>

      {a.rationale && (
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          {a.rationale}
        </p>
      )}

      {/* Who exactly receives it — the list behind the count. */}
      {a.kind === "email" && (
        <RecipientList
          campaignId={a.campaign_id}
          step={a.step}
          total={a.audience_size}
        />
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
            <p className="px-4 pb-2 text-sm text-brand">
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
                Use this exact link. It records the click and tags the visit
                with its platform — that is how a post you publish yourself
                still shows up in your analytics.
              </p>
            </div>
          )}
        </div>
      )}

      <div className="mt-3 flex items-center gap-2">
        <Done onClick={() => onDone(a)} busy={busyKey === key} />
        <span className="text-xs text-slate-400">
          Mark it done once you have sent or published it.
        </span>
      </div>
    </Card>
  );
}

const tabClass = (active: boolean) =>
  `inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
    active
      ? "bg-brand text-white shadow-sm"
      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
  }`;

const subTabClass = (active: boolean) =>
  `rounded-full px-3 py-1 text-xs font-semibold transition ${
    active
      ? "bg-slate-800 text-white"
      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
  }`;

export function ActionPlan({ actions }: { actions: PlanAction[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);

  const emails = actions.filter((a) => a.kind === "email");
  const posts = actions.filter((a) => a.kind === "post");
  const platforms = [...new Set(posts.map((p) => p.platform ?? "other"))];

  const [tab, setTab] = useState<"email" | "post">(
    emails.length > 0 ? "email" : "post",
  );
  const [platformTab, setPlatformTab] = useState<string>("all");

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

  const visiblePosts =
    platformTab === "all"
      ? posts
      : posts.filter((p) => (p.platform ?? "other") === platformTab);

  return (
    <div>
      {/* Channel tabs */}
      <div className="mb-3 flex gap-2">
        <button onClick={() => setTab("email")} className={tabClass(tab === "email")}>
          <Mail size={14} />
          Email ({emails.length})
        </button>
        <button onClick={() => setTab("post")} className={tabClass(tab === "post")}>
          <Megaphone size={14} />
          Posts ({posts.length})
        </button>
      </div>

      {/* Platform sub-tabs, only for posts */}
      {tab === "post" && platforms.length > 1 && (
        <div className="mb-4 flex flex-wrap gap-1.5">
          <button
            onClick={() => setPlatformTab("all")}
            className={subTabClass(platformTab === "all")}
          >
            All ({posts.length})
          </button>
          {platforms.map((p) => (
            <button
              key={p}
              onClick={() => setPlatformTab(p)}
              className={subTabClass(platformTab === p)}
            >
              {platformLabel(p)} (
              {posts.filter((x) => (x.platform ?? "other") === p).length})
            </button>
          ))}
        </div>
      )}

      <div className="space-y-4">
        {tab === "email" ? (
          emails.length ? (
            emails.map((a, i) => (
              <ActionCard
                key={`e${a.campaign_id}-${a.step}-${i}`}
                a={a}
                index={i}
                busyKey={busy}
                onDone={markDone}
              />
            ))
          ) : (
            <Card>
              <p className="text-sm text-slate-500">
                No email actions in this plan.
              </p>
            </Card>
          )
        ) : visiblePosts.length ? (
          visiblePosts.map((a, i) => (
            <ActionCard
              key={`p${a.id}-${i}`}
              a={a}
              index={i}
              busyKey={busy}
              onDone={markDone}
            />
          ))
        ) : (
          <Card>
            <p className="text-sm text-slate-500">
              No post actions in this plan.
            </p>
          </Card>
        )}
      </div>
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
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm
                     text-slate-800 transition focus:border-brand"
        >
          <option value="hybrid">Hybrid — segment-aware, behaviour-driven</option>
          <option value="trigger">Trigger — one message, then react</option>
          <option value="fixed">Fixed — the whole sequence upfront</option>
        </select>
        <button
          onClick={run}
          disabled={busy}
          className="rounded-lg bg-brand px-4 py-2 text-sm font-bold text-white
                     transition hover:bg-brand-strong disabled:opacity-60"
        >
          {busy ? "Planning…" : "Generate action plan"}
        </button>
      </div>
    </Card>
  );
}
