import { API_URL } from "@/lib/api";
import type {
  MetricValue,
  ModuleResearchResult,
  ResearchExperiment,
  ResearchRow,
  ResearchTable,
} from "@/lib/api";
import { Card, Caveat, EmptyState, Pill, SectionLabel } from "@/components/ui";

/**
 * The Live view / Research results switch, shared by every module page.
 *
 * A plain link pair rather than client-side state: these pages are server
 * components, so putting the view in the URL means the server renders the
 * right one directly and the tab is linkable — the same reasoning as SearchBox.
 */
export function ViewTabs({ view }: { view: "live" | "research" }) {
  const style = (active: boolean) =>
    `rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
      active
        ? "bg-brand text-white shadow-sm"
        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
    }`;
  return (
    <div className="mb-4 flex gap-2">
      <a href="?" className={style(view !== "research")}>
        Live view
      </a>
      <a href="?view=research" className={style(view === "research")}>
        Research results
      </a>
    </div>
  );
}

/** "goal_best_macro_f1" -> "goal best macro f1" */
const humanize = (key: string) => key.replace(/_/g, " ");

/** "e6_model_summary" -> "MODEL SUMMARY" — the E-number is already on the card. */
const tableLabel = (name: string) =>
  name
    .replace(/^e\d+_/, "")
    .replace(/_/g, " ")
    .toUpperCase();

/**
 * Four significant figures, never at the cost of the number's meaning.
 *
 * A fixed 4 decimal places would print a Wilcoxon p of 1.9e-9 as "0" and a
 * Holm threshold of 0.00625 as "0.0063" — for a p-value the magnitude IS the
 * result, so small values keep their precision and very small ones switch to
 * exponential rather than round away.
 */
function formatNumber(n: number): string {
  if (Number.isInteger(n)) return n.toLocaleString();
  if (Math.abs(n) < 1e-4) return n.toExponential(2);
  if (Math.abs(n) < 1) return String(Number(n.toPrecision(4)));
  return n.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
}

function formatValue(value: MetricValue): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "number") return formatNumber(value);
  if (Array.isArray(value)) {
    // A two-number array is a confidence interval everywhere in these results.
    const parts = value.map((v) =>
      typeof v === "number" ? formatNumber(v) : String(v),
    );
    return value.length === 2 && value.every((v) => typeof v === "number")
      ? `${parts[0]} to ${parts[1]}`
      : parts.join(", ");
  }
  return String(value);
}

function StatusPill({ status }: { status: string }) {
  if (status === "ok") return null;
  return <Pill tone={status === "failed" ? "bad" : "warn"}>{status}</Pill>;
}

/**
 * One result table. Columns are whatever the experiment wrote, so they are
 * driven by the payload rather than declared here — a new column in an
 * experiment shows up without a frontend change.
 */
function DynamicTable({ table }: { table: ResearchTable }) {
  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left">
              {table.columns.map((c) => (
                <th
                  key={c}
                  className="py-2 pr-4 text-xs font-bold uppercase tracking-wide text-slate-400"
                >
                  {humanize(c)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row: ResearchRow, i: number) => (
              <tr key={i} className="border-b border-slate-100 last:border-0">
                {table.columns.map((c) => (
                  <td
                    key={c}
                    className="whitespace-nowrap py-2.5 pr-4 text-slate-700"
                  >
                    {formatValue(row[c] ?? null)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {table.truncated && (
        <p className="mt-2 text-xs text-slate-400">
          Showing {table.rows.length} of {table.row_count.toLocaleString()} rows
          — the full table is in{" "}
          <code className="text-slate-500">
            research/results/{table.name}.csv
          </code>
          .
        </p>
      )}
    </>
  );
}

function ExperimentCard({ exp }: { exp: ResearchExperiment }) {
  const metrics = Object.entries(exp.metrics ?? {});

  return (
    <Card className="mt-4">
      <div className="flex flex-wrap items-center gap-2">
        <Pill tone="brand">{exp.id}</Pill>
        <p className="font-bold text-slate-700">{exp.short_title}</p>
        <StatusPill status={exp.status} />
      </div>
      {exp.reason && (
        <p className="mt-2 text-sm text-slate-500">{exp.reason}</p>
      )}

      {metrics.length > 0 && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {metrics.map(([key, value]) => (
            <div key={key} className="rounded-lg bg-slate-50 px-3 py-2">
              <p className="text-[0.65rem] font-bold uppercase tracking-wide text-slate-400">
                {humanize(key)}
              </p>
              <p className="mt-0.5 text-sm font-semibold text-slate-700">
                {formatValue(value)}
              </p>
            </div>
          ))}
        </div>
      )}

      {exp.tables.map((table) => (
        <div key={table.name} className="mt-5">
          <SectionLabel>{tableLabel(table.name)}</SectionLabel>
          <div className="mt-2">
            <DynamicTable table={table} />
          </div>
        </div>
      ))}

      {exp.figures.length > 0 && (
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          {exp.figures.map((name) => (
            <figure key={name}>
              {/* Served by /research/figures/{name} against an allowlist of the
                  figures the run produced — the same PNG the report prints. */}
              <img
                src={`${API_URL}/research/figures/${name}`}
                alt={`${exp.id} — ${exp.short_title}`}
                className="w-full rounded-lg border border-slate-200"
              />
              <figcaption className="mt-1 text-xs text-slate-500">
                {name}
              </figcaption>
            </figure>
          ))}
        </div>
      )}

      {/* Notes are the caveats the experiment attached to its own numbers.
          They are not decoration: several of them say the result went against
          the hypothesis, and dropping them would misrepresent the finding. */}
      {exp.notes.map((note, i) => (
        <Caveat key={i}>{note}</Caveat>
      ))}
    </Card>
  );
}

/**
 * A module's research results — read from research/results/results.json via
 * /research/modules/{n}/results, never hardcoded here. This is the measured
 * research output that the report cites, distinct from the operational live
 * view on the same page.
 */
export function ModuleResearch({
  data,
  module,
}: {
  data: ModuleResearchResult | null;
  module: number;
}) {
  if (!data) {
    return (
      <EmptyState
        title="Cannot reach the research API"
        body="The Research results tab reads the experiment layer through the API, and that request failed. Start the API, then reload."
        hint="venv/bin/uvicorn api.main:app --port 8000 --reload"
      />
    );
  }

  if (!data.available) {
    return (
      <EmptyState
        title="Experiments not run yet"
        body={`This view reads the experiment layer's own results file — Module ${module}'s experiments have not been run on this machine yet.`}
        hint="venv/bin/python -m research.run_all"
      />
    );
  }

  const ids = data.experiments.map((e) => e.id).join(", ");
  const meta = data.meta;

  return (
    <>
      <Card>
        <SectionLabel>
          MODULE {data.module} — {(data.module_name ?? "").toUpperCase()} ({ids})
        </SectionLabel>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          What this module was actually measured to do. Every number below is
          read from <code>research/results/results.json</code>, written by{" "}
          <code>{meta?.generated_by ?? "research/run_all.py"}</code> — the same
          file the report is built from, so the two cannot disagree.
        </p>
        {meta && (
          <p className="mt-2 text-xs text-slate-400">
            seed {meta.seed} · {meta.n_bootstrap?.toLocaleString()} bootstrap
            resamples · {meta.n_seeds} seeds where an experiment repeats a run
          </p>
        )}
      </Card>

      {data.experiments.map((exp) => (
        <ExperimentCard key={exp.id} exp={exp} />
      ))}
    </>
  );
}
