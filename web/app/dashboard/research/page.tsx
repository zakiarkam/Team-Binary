import {
  Card,
  Caveat,
  ErrorState,
  Kpi,
  PageHeader,
  Pill,
  SectionLabel,
  Table,
} from "@/components/ui";
import { safeGet } from "@/lib/api";

export const dynamic = "force-dynamic";

interface DatasetRow {
  key: string;
  name: string;
  path: string;
  nature: string;
  origin: string;
  used_by: string[];
  note: string;
  rows: number | null;
  present: boolean;
  unused: boolean;
}

interface ModelRow {
  key: string;
  name: string;
  kind: string;
  headline: string;
  honest: string;
  dataset_name: string;
  dataset_nature: string;
  dataset_rows: number | null;
  artifact_present: boolean;
}

interface Provenance {
  datasets: DatasetRow[];
  models: ModelRow[];
  goal_tone_metrics: {
    dataset_rows: number;
    results: {
      target: string;
      model: string;
      accuracy: number;
      weighted_f1: number;
      macro_f1: number;
    }[];
  } | null;
  live: {
    visitors?: { total: number; dataset: number; live: number };
    interactions?: { total: number; dataset: number; live: number };
    live_share: number | null;
    note?: string;
    caveat?: string;
  };
  summary: {
    n_datasets: number;
    n_present: number;
    n_unused: number;
    real_datasets: number;
    simulated_or_synthetic: number;
  };
}

const NATURE_TONE: Record<string, "ok" | "warn" | "muted"> = {
  real: "ok",
  simulated: "warn",
  synthetic: "warn",
  derived: "muted",
};

export default async function ResearchPage() {
  const prov = await safeGet<Provenance>("/research/provenance");
  if (!prov) return <ErrorState error="Could not load research provenance." />;

  const { summary, live } = prov;

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        crumb="Dashboard"
        title="Research"
        subtitle="The evidence behind every number this system shows."
      />

      <Card className="mb-4">
        <SectionLabel>WHY THIS PAGE EXISTS</SectionLabel>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          The largest risk in this project is not a wrong model — it is a reader
          assuming a figure measured real behaviour when it did not. Everything
          below is read from the repository and the database at the moment you
          load the page, so it cannot drift away from what is actually there the
          way a hand-written table in a report can.
        </p>
      </Card>

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi
          label="DATASETS"
          value={summary.n_datasets}
          hint={`${summary.n_present} present on disk`}
        />
        <Kpi
          label="REAL-WORLD DATA"
          value={summary.real_datasets}
          hint="observed from real people"
          tone="ok"
        />
        <Kpi
          label="SIMULATED / SYNTHETIC"
          value={summary.simulated_or_synthetic}
          hint="generated, not observed"
          tone="warn"
        />
        <Kpi
          label="UNUSED"
          value={summary.n_unused}
          hint="shipped but read by no code"
          tone="bad"
        />
      </section>

      <Card className="mt-4">
        <SectionLabel>WHAT THIS DASHBOARD IS CURRENTLY SHOWING</SectionLabel>
        <div className="mt-3 grid gap-4 md:grid-cols-2">
          <div className="text-sm text-slate-600">
            <p>
              <b className="text-slate-800">{live.visitors?.dataset ?? 0}</b>{" "}
              customers imported from the research dataset and{" "}
              <b className="text-slate-800">{live.visitors?.live ?? 0}</b> from
              live browser sessions.
            </p>
            <p className="mt-1">
              <b className="text-slate-800">{live.interactions?.live ?? 0}</b>{" "}
              of {live.interactions?.total ?? 0} funnel events came from live
              traffic
              {live.live_share != null &&
                ` (${(live.live_share * 100).toFixed(0)}%)`}
              .
            </p>
          </div>
          <p className="text-xs leading-relaxed text-slate-500">{live.note}</p>
        </div>
        {live.caveat && <Caveat>{live.caveat}</Caveat>}
      </Card>

      <Card className="mt-4">
        <SectionLabel>DATASETS — WHAT TRAINED WHAT</SectionLabel>
        <Table
          rows={prov.datasets}
          columns={[
            {
              key: "name",
              header: "Dataset",
              render: (d) => (
                <div>
                  <p className="font-medium text-slate-800">{d.name}</p>
                  <p className="font-mono text-[0.7rem] text-slate-400">
                    {d.path}
                  </p>
                </div>
              ),
            },
            {
              key: "rows",
              header: "Rows",
              render: (d) =>
                d.rows == null ? (
                  <span className="text-red-500">missing</span>
                ) : (
                  d.rows.toLocaleString()
                ),
            },
            {
              key: "nature",
              header: "Nature",
              render: (d) => (
                <Pill tone={NATURE_TONE[d.nature] ?? "muted"}>{d.nature}</Pill>
              ),
            },
            {
              key: "used_by",
              header: "Used by",
              render: (d) =>
                d.used_by.length ? (
                  <span className="text-slate-600">{d.used_by.join(", ")}</span>
                ) : (
                  <span className="font-semibold text-red-600">
                    nothing reads this
                  </span>
                ),
            },
          ]}
        />
        <Caveat>
          Three real platform datasets ship with the project but no code reads
          them. That is listed here rather than left out — a per-platform
          engagement model is the obvious use for them, and until that exists
          the engagement regressor rests on a synthetic corpus.
        </Caveat>
      </Card>

      <Card className="mt-4">
        <SectionLabel>MODELS — HEADLINE VERSUS HONEST</SectionLabel>
        <div className="mt-3 space-y-4">
          {prov.models.map((m) => (
            <div key={m.key} className="rounded-xl border border-slate-200 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-slate-800">{m.name}</span>
                <Pill tone={NATURE_TONE[m.dataset_nature] ?? "muted"}>
                  {m.dataset_nature}
                </Pill>
                {!m.artifact_present && (
                  <Pill tone="bad">artifact missing</Pill>
                )}
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {m.kind} · trained on {m.dataset_name}
                {m.dataset_rows != null &&
                  ` (${m.dataset_rows.toLocaleString()} rows)`}
              </p>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <div className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-[0.65rem] font-bold uppercase tracking-wide text-slate-400">
                    Headline
                  </p>
                  <p className="text-sm text-slate-700">{m.headline}</p>
                </div>
                <div className="rounded-lg bg-amber-50 px-3 py-2">
                  <p className="text-[0.65rem] font-bold uppercase tracking-wide text-amber-700">
                    What it actually means
                  </p>
                  <p className="text-sm leading-relaxed text-amber-900">
                    {m.honest}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {prov.goal_tone_metrics && (
        <Card className="mt-4">
          <SectionLabel>
            GOAL / TONE CLASSIFIERS — MEASURED, FROM THE TRAINING ARTIFACT
          </SectionLabel>
          <Table
            rows={prov.goal_tone_metrics.results}
            columns={[
              { key: "target", header: "Target" },
              { key: "model", header: "Model" },
              {
                key: "accuracy",
                header: "Accuracy",
                render: (r) => r.accuracy.toFixed(3),
              },
              {
                key: "weighted_f1",
                header: "Weighted F1",
                render: (r) => r.weighted_f1.toFixed(3),
              },
              {
                key: "macro_f1",
                header: "Macro F1",
                render: (r) => r.macro_f1.toFixed(3),
              },
            ]}
          />
          <Caveat>
            Trained on {prov.goal_tone_metrics.dataset_rows} labelled rows. The
            gap between weighted F1 and macro F1 is the story: the classifier
            does well on the common classes and poorly on the rare ones, which
            an accuracy figure alone would hide.
          </Caveat>
        </Card>
      )}

      <Card className="mt-4">
        <SectionLabel>KNOWN LIMITATIONS</SectionLabel>
        <ul className="mt-3 space-y-2 text-sm leading-relaxed text-slate-600">
          <li>
            <b>Attribution needs multi-platform journeys.</b> Email alone is one
            platform, and every attribution model agrees on a single-platform
            journey by construction. The journey therefore joins the acquisition
            channel to the email touches, and the share of single-touch journeys
            is reported alongside every attribution result.
          </li>
          <li>
            <b>
              The conversion and drop-off models were fitted on a simulator.
            </b>{" "}
            Using them on a live audience is a transfer across distributions.
            They rank usefully; their thresholds do not carry over, and the
            analytics service raises a calibration warning when they collapse.
          </li>
          <li>
            <b>Open rates under-report.</b> Most mail clients block the tracking
            pixel, so a missing open does not mean the message went unread.
            Click-through is the reliable engagement signal.
          </li>
          <li>
            <b>The goal and tone classifiers are low-data.</b> ~113 labelled
            rows is small enough that a single train/test split is noisy.
          </li>
          <li>
            <b>Segment clusters overlap.</b> Silhouette 0.087 on the research
            dataset. The segments separate conversion by 38 points while still
            being geometrically untidy — both are true.
          </li>
        </ul>
      </Card>
    </div>
  );
}
