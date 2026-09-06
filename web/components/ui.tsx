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

/* ---------------------------------------------------------------------------
   Form + action primitives. Every button, input and select in the app comes
   from here so sizing, radius and focus treatment stay identical everywhere.
   --------------------------------------------------------------------------- */

const BUTTON_VARIANTS = {
  primary: "bg-brand text-white hover:bg-brand-strong",
  dark: "bg-slate-800 text-white hover:bg-slate-700",
  outline: "border border-line bg-white text-slate-700 hover:bg-slate-50",
  ghost: "text-slate-600 hover:bg-slate-100",
  danger: "bg-bad text-white hover:bg-red-700",
} as const;

const BUTTON_SIZES = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
  lg: "px-4 py-2.5 text-sm",
} as const;

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  ...props
}: {
  variant?: keyof typeof BUTTON_VARIANTS;
  size?: keyof typeof BUTTON_SIZES;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-lg
                  font-semibold transition disabled:cursor-not-allowed
                  disabled:opacity-60 ${BUTTON_VARIANTS[variant]}
                  ${BUTTON_SIZES[size]} ${className}`}
    />
  );
}

export const INPUT_CLASS =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm " +
  "text-slate-800 placeholder:text-slate-400 transition focus:border-brand";

export function Input({
  className = "",
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${INPUT_CLASS} ${className}`} />;
}

export function Textarea({
  className = "",
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`${INPUT_CLASS} ${className}`} />;
}

export function Select({
  className = "",
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`${INPUT_CLASS} ${className}`} />;
}

/** A labelled input  the one form field pattern used across the app. */
export function Field({
  label,
  hint,
  as = "input",
  ...props
}: {
  label: string;
  hint?: string;
  as?: "input" | "textarea";
} & React.InputHTMLAttributes<HTMLInputElement> &
  React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
        {label}
      </span>
      {as === "textarea" ? (
        <Textarea className="mt-1" {...props} />
      ) : (
        <Input className="mt-1" {...props} />
      )}
      {hint && (
        <span className="mt-1 block text-xs text-slate-400">{hint}</span>
      )}
    </label>
  );
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
  // Tones map onto the soft/strong token pairs in globals.css @theme, so a
  // pill, a KPI and a chart series showing the same state share one colour.
  const styles = {
    ok: "bg-ok-soft text-green-700",
    warn: "bg-warn-soft text-warn",
    bad: "bg-bad-soft text-bad",
    muted: "bg-slate-100 text-slate-600",
    // Neutral-but-distinct: used to tell one channel from another on the
    // Action Plan, where the tone carries no judgement about quality.
    brand: "bg-brand-soft text-brand",
    accent: "bg-accent-soft text-accent",
  } as const;
  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-bold ${styles[tone]}`}
    >
      {children}
    </span>
  );
}

/**
 * Says which audience a figure rests on.
 *
 * Shown next to every number that could be mistaken for a result. Imported
 * research users flow through the same write paths as a live browser, so
 * without this badge a screenshot of the dashboard could not be told apart
 * from one taken over live traffic.
 */
export function BasisBadge({ basis }: { basis: DataBasis }) {
  if (!basis || basis === "no data yet") {
    return <Pill tone="muted">no data yet</Pill>;
  }
  if (basis === "live") return <Pill tone="ok">live traffic</Pill>;
  if (basis === "mixed") return <Pill tone="warn">dataset + live</Pill>;
  return <Pill tone="muted">research dataset</Pill>;
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

/**
 * A search box that works without client-side JavaScript.
 *
 * These pages are server components, and an audience of several thousand needs
 * to be searchable rather than scrolled. A plain GET form puts the query in the
 * URL, which means the server renders the filtered page directly, the result is
 * linkable and bookmarkable, and the back button behaves — none of which comes
 * for free with client-side filtering. `hidden` carries any other filters
 * already in the URL so searching does not silently discard them.
 */
export function SearchBox({
  action,
  placeholder,
  value,
  hidden = {},
}: {
  action: string;
  placeholder: string;
  value?: string;
  hidden?: Record<string, string | undefined>;
}) {
  return (
    <form action={action} method="get" className="flex gap-2">
      {Object.entries(hidden).map(([k, v]) =>
        v ? <input key={k} type="hidden" name={k} value={v} /> : null,
      )}
      <input
        type="search"
        name="q"
        defaultValue={value ?? ""}
        placeholder={placeholder}
        aria-label={placeholder}
        className="w-56 rounded-lg border border-slate-300 bg-white px-3 py-1.5
                   text-sm placeholder:text-slate-400 transition focus:border-brand"
      />
      <Button type="submit" size="sm" variant="primary">
        Search
      </Button>
      {value ? (
        <a
          href={action}
          className="self-center text-sm text-slate-500 hover:text-slate-800"
        >
          Clear
        </a>
      ) : null}
    </form>
  );
}

/**
 * Previous / next links over a paged list.
 *
 * Says how many rows are being shown out of how many exist — a table that
 * silently shows the first 15 of 8,000 reads as though 15 is all there is.
 */
export function Pagination({
  action,
  total,
  limit,
  offset,
  params = {},
}: {
  action: string;
  total: number;
  limit: number;
  offset: number;
  params?: Record<string, string | undefined>;
}) {
  const query = (next: number) => {
    const search = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) if (v) search.set(k, v);
    if (next > 0) search.set("offset", String(next));
    const s = search.toString();
    return s ? `${action}?${s}` : action;
  };

  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);
  const hasPrevious = offset > 0;
  const hasNext = to < total;

  return (
    <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
      <span>
        {from.toLocaleString()}–{to.toLocaleString()} of{" "}
        <b className="text-slate-700">{total.toLocaleString()}</b>
      </span>
      <span className="flex gap-3">
        {hasPrevious ? (
          <a
            className="font-medium text-slate-700 hover:underline"
            href={query(Math.max(0, offset - limit))}
          >
            ← Previous
          </a>
        ) : (
          <span className="text-slate-300">← Previous</span>
        )}
        {hasNext ? (
          <a
            className="font-medium text-slate-700 hover:underline"
            href={query(offset + limit)}
          >
            Next →
          </a>
        ) : (
          <span className="text-slate-300">Next →</span>
        )}
      </span>
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
