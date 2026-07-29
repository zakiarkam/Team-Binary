import type { DataBasis } from "@/lib/api";

/** Standard white surface used for every panel. */
export function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <section className={`card ${className}`}>{children}</section>;
}

export function PageHeader({
  crumb,
  title,
  subtitle,
}: {
  crumb: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <header className="mb-6">
      <p className="text-sm font-semibold text-slate-400">{crumb}</p>
      <h1 className="text-2xl font-extrabold tracking-tight">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
    </header>
  );
}

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return <p className="label">{children}</p>;
}

// Semantic tokens declared in globals.css @theme, so a palette change happens
// in one place rather than across every component.
const TONES = {
  brand: "text-brand",
  ok: "text-ok",
  info: "text-info",
  accent: "text-accent",
  warn: "text-warn",
  bad: "text-bad",
  ink: "text-ink",
} as const;

export type Tone = keyof typeof TONES;

export function Kpi({
  label,
  value,
  hint,
  tone = "brand",
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: Tone;
}) {
  return (
    <div className="card">
      <p className="label">{label}</p>
      <p className={`mt-1 text-3xl font-extrabold ${TONES[tone]}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

export function Pill({
  tone = "ok",
  children,
}: {
  tone?: "ok" | "warn" | "bad" | "muted" | "brand" | "accent";
  children: React.ReactNode;
}) {
  const styles = {
    ok: "bg-green-100 text-green-700",
    warn: "bg-amber-100 text-amber-700",
    bad: "bg-red-100 text-red-700",
    muted: "bg-slate-100 text-slate-600",
    // Neutral-but-distinct: used to tell one channel from another on the
    // Action Plan, where the tone carries no judgement about quality.
    brand: "bg-indigo-100 text-indigo-700",
    accent: "bg-violet-100 text-violet-700",
  } as const;
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-bold ${styles[tone]}`}>
      {children}
    </span>
  );
}

/**
 * Says whether a figure rests on real people or simulated traffic.
 *
 * Shown next to every number that could be mistaken for a result. Demo traffic
 * flows through the same endpoints as real visitors, so without this badge a
 * screenshot of the dashboard would be indistinguishable from a real one.
 */
export function BasisBadge({ basis }: { basis: DataBasis }) {
  if (!basis || basis === "no data yet") {
    return <Pill tone="muted">no data yet</Pill>;
  }
  if (basis === "real") return <Pill tone="ok">real data</Pill>;
  if (basis === "mixed") return <Pill tone="warn">real + simulated</Pill>;
  return <Pill tone="warn">simulated data</Pill>;
}

export function EmptyState({
  title,
  body,
  hint,
}: {
  title: string;
  body: string;
  hint?: string;
}) {
  return (
    <Card>
      <p className="font-bold text-slate-700">{title}</p>
      <p className="mt-1 text-sm text-slate-500">{body}</p>
      {hint && <code className="snippet mt-3">{hint}</code>}
    </Card>
  );
}

export function ErrorState({ error }: { error: string }) {
  return (
    <Card className="border-l-4 border-red-500">
      <p className="font-bold text-red-700">Cannot reach the API</p>
      <p className="mt-1 text-sm text-slate-600">{error}</p>
      <code className="snippet mt-3">
        venv/bin/uvicorn api.main:app --reload --port 8000
      </code>
    </Card>
  );
}

/** A caveat the reader needs in order to interpret the number above it. */
export function Caveat({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-3 border-l-2 border-amber-300 bg-amber-50/60 px-3 py-2 text-xs leading-relaxed text-amber-900">
      {children}
    </p>
  );
}

export function Bar({
  label,
  value,
  max,
  suffix,
  color = "#3b5bdb",
}: {
  label: string;
  value: number;
  max: number;
  suffix?: string;
  color?: string;
}) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="mb-3">
      <div className="mb-1 flex justify-between text-sm">
        <span className="text-slate-600">{label}</span>
        <span className="font-semibold text-slate-700">
          {suffix ?? value.toLocaleString()}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

// `object` rather than Record<string, unknown>: a TypeScript *interface* has no
// implicit index signature, so the stricter constraint rejects every typed row
// the API client returns.
export function Table<T extends object>({
  columns,
  rows,
  empty = "Nothing to show yet.",
}: {
  columns: {
    key: keyof T & string;
    header: string;
    render?: (row: T) => React.ReactNode;
  }[];
  rows: T[];
  empty?: string;
}) {
  if (rows.length === 0) {
    return <p className="py-4 text-sm text-slate-400">{empty}</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left">
            {columns.map((c) => (
              <th
                key={c.key}
                className="py-2 pr-4 text-xs font-bold uppercase tracking-wide text-slate-400"
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-slate-100 last:border-0">
              {columns.map((c) => (
                <td key={c.key} className="py-2.5 pr-4 text-slate-700">
                  {c.render ? c.render(row) : String(row[c.key] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export const SEGMENT_COLOR: Record<string, string> = {
  "High Intent": "#16a34a",
  "Loyal Customer": "#3b5bdb",
  "Price Sensitive": "#f59e0b",
  "Low Engagement": "#ea580c",
  "New Cold User": "#8b5cf6",
};

export const PLATFORM_COLOR: Record<string, string> = {
  email: "#059669",
  instagram: "#e1306c",
  linkedin: "#0a66c2",
  tiktok: "#111827",
  shorts: "#ff0000",
  facebook: "#1877f2",
  google: "#ea4335",
  newsletter: "#0ea5e9",
  direct: "#64748b",
};

export const pct = (n: number | null | undefined, digits = 1) =>
  n == null ? "—" : `${(n * 100).toFixed(digits)}%`;
