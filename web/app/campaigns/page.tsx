import { StrategyChart } from "@/components/charts";
import {
  BasisBadge,
  Card,
  Caveat,
  EmptyState,
  ErrorState,
  Kpi,
  PageHeader,
  Pill,
  SectionLabel,
  Table,
  pct,
} from "@/components/ui";
import { API_URL, safeGet } from "@/lib/api";
import type {
  CampaignMetrics,
  Module2ResearchResult,
  ReachableAudience,
} from "@/lib/api";
import { currentSite } from "@/lib/site";

export const dynamic = "force-dynamic";

const STRATEGY_BLURB: Record<string, string> = {
  fixed: "Everyone gets the same sequence on the same schedule.",
  trigger: "Only the opener is scheduled; what follows depends on behaviour.",
  hybrid: "A fixed backbone, adjusted by segment and predicted conversion.",
};

export default async function CampaignsPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const params = await searchParams;
  const view = params.view === "research" ? "research" : "live";

  const { site, health, error } = await currentSite();
  if (error) return <ErrorState error={error} />;
  if (!site) {
    return (
      <>
        <PageHeader crumb="Dashboard" title="Campaigns" />
        <EmptyState
          title="No website registered yet"
          body="Register a site before running campaigns."
          hint="venv/bin/python scripts/setup_demo_site.py"
        />
      </>
    );
  }

  const [list, reach] = await Promise.all([
    safeGet<{ campaigns: CampaignMetrics[]; email_delivery: string }>(
      `/sites/${site.id}/campaigns`,
    ),
    safeGet<ReachableAudience>(`/sites/${site.id}/audience/reachable`),
  ]);

  // Additive: only fetched when the research view is open, and independent
  // of the live campaign data above.
  const research =
    view === "research"
      ? await safeGet<Module2ResearchResult>("/research/m2/results")
      : null;

  const campaigns = list?.campaigns ?? [];
  const dryRun = (list?.email_delivery ?? health?.email_delivery) !== "live";

  const totals = campaigns.reduce(
    (acc, c) => ({
      sent: acc.sent + c.sent,
      opens: acc.opens + c.opens,
      clicks: acc.clicks + c.clicks,
      conversions: acc.conversions + c.conversions,
    }),
    { sent: 0, opens: 0, clicks: 0, conversions: 0 },
  );

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        crumb="Dashboard"
        title="Campaigns"
        subtitle="Module 2 — fixed, trigger and hybrid automation on one audience."
      />

      <div className="mb-4 flex gap-2">
        <a
          href="?"
          className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
            view !== "research"
              ? "bg-slate-800 text-white"
              : "bg-slate-100 text-slate-600 hover:bg-slate-200"
          }`}
        >
          Live view
        </a>
        <a
          href="?view=research"
          className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
            view === "research"
              ? "bg-slate-800 text-white"
              : "bg-slate-100 text-slate-600 hover:bg-slate-200"
          }`}
        >
          Research results
        </a>
      </div>

      {view === "research" ? (
        <ResearchView data={research} />
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <Pill tone={dryRun ? "warn" : "ok"}>
              {dryRun ? "email: dry run — nothing is sent" : "email: live"}
            </Pill>
            {reach && (
              <span className="text-sm text-slate-500">
                <b className="text-slate-700">{reach.reachable}</b> contactable of{" "}
                {reach.visitors} visitors
              </span>
            )}
          </div>

          {campaigns.length === 0 ? (
            <EmptyState
              title="No campaigns yet"
              body="Run all three automation policies over the same audience and compare them."
              hint="venv/bin/python scripts/run_strategy_comparison.py --site-id 1 --reset --simulate-engagement"
            />
          ) : (
            <>
              <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                <Kpi label="MESSAGES SENT" value={totals.sent.toLocaleString()} />
                <Kpi label="OPENS" value={totals.opens.toLocaleString()} tone="info" />
                <Kpi label="CLICKS" value={totals.clicks.toLocaleString()} tone="warn" />
                <Kpi label="CONVERSIONS" value={totals.conversions.toLocaleString()} tone="ok" />
              </section>

              <Card className="mt-4">
                <div className="flex items-center justify-between">
                  <SectionLabel>STRATEGY COMPARISON</SectionLabel>
                  <BasisBadge basis={campaigns[0]?.data_basis ?? null} />
                </div>
                <Table
                  rows={campaigns}
                  columns={[
                    { key: "strategy", header: "Strategy" },
                    { key: "recipients", header: "Recipients" },
                    { key: "sent", header: "Sent" },
                    { key: "opens", header: "Opens" },
                    { key: "clicks", header: "Clicks" },
                    { key: "conversions", header: "Conv." },
                    {
                      key: "click_through_rate",
                      header: "CTR",
                      render: (c) => pct(c.click_through_rate),
                    },
                    {
                      key: "conversions_per_1000_sends",
                      header: "Conv / 1k sends",
                      render: (c) => c.conversions_per_1000_sends.toFixed(1),
                    },
                    {
                      key: "operational_complexity",
                      header: "Rules",
                      render: (c) => (
                        <span title="Number of distinct decision rules the policy needs">
                          {c.operational_complexity}
                        </span>
                      ),
                    },
                  ]}
                />
                <Caveat>
                  <b>Conversions per 1,000 sends</b> is the fair efficiency measure —
                  a fixed workflow can win on raw conversions simply by sending five
                  times as many messages. <b>Rules</b> is the operational-complexity
                  metric: a policy that wins narrowly while needing eight decision
                  rules instead of one is not obviously the better choice.
                </Caveat>
              </Card>

              <div className="mt-4 grid gap-4 lg:grid-cols-2">
                <Card>
                  <SectionLabel>EFFICIENCY — CONVERSIONS PER 1,000 SENDS</SectionLabel>
                  <StrategyChart campaigns={campaigns}
                                 metric="conversions_per_1000_sends"
                                 label="Conversions / 1k" />
                </Card>
                <Card>
                  <SectionLabel>OPERATIONAL COMPLEXITY — DECISION RULES</SectionLabel>
                  <StrategyChart campaigns={campaigns}
                                 metric="operational_complexity"
                                 label="Rules" />
                </Card>
              </div>

              <div className="mt-4 grid gap-4 lg:grid-cols-3">
                {campaigns.map((c) => (
                  <Card key={c.id}>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                          {c.strategy}
                        </p>
                        <p className="font-semibold text-slate-800">{c.name}</p>
                      </div>
                      <Pill tone={c.status === "running" ? "ok" : "muted"}>
                        {c.status}
                      </Pill>
                    </div>
                    <p className="mt-2 text-xs leading-relaxed text-slate-500">
                      {STRATEGY_BLURB[c.strategy]}
                    </p>
                    <dl className="mt-3 space-y-1 text-sm">
                      <Row label="Open rate" value={pct(c.open_rate)} />
                      <Row label="Click-through" value={pct(c.click_through_rate)} />
                      <Row label="Conversion" value={pct(c.conversion_rate)} />
                      <Row label="Unsubscribes" value={String(c.unsubscribes)} />
                      <Row label="Still queued" value={String(c.pending)} />
                    </dl>
                  </Card>
                ))}
              </div>

              <Card className="mt-4">
                <SectionLabel>HOW TO READ THE OPEN RATE</SectionLabel>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">
                  {campaigns[0]?.caveat}
                </p>
              </Card>
            </>
          )}
        </>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-semibold text-slate-700">{value}</dd>
    </div>
  );
}

const FIGURE_CAPTIONS: Record<string, string> = {
  "strategy_comparison_bars.png": "Three-way comparison — engagement, conversion and complexity side by side.",
  "funnel_by_strategy.png": "Sent → open → click → convert funnel, one line per strategy.",
  "sparsity_sweep.png": "Efficiency as signal sparsity rises from 0.0 to 0.99 — the cold-start sweep.",
  "complexity_vs_performance.png": "Operational complexity against conversions per 1,000 sends.",
  "hybrid_routing_breakdown.png": "How the hybrid strategy splits users across its fallback, trigger and blended paths.",
  "ml_model_diagnostics.png": "The ML routing model's ROC and precision-recall behaviour.",
};

/**
 * Module 2's real research output — read from the pipeline's own result
 * files via /research/m2/results, never hardcoded here. Distinct from the
 * live view above: this is the controlled-simulation measurement.
 */
function ResearchView({ data }: { data: Module2ResearchResult | null }) {
  if (!data || !data.available) {
    return (
      <EmptyState
        title="Research results not generated yet"
        body="This view reads Module 2's own pipeline output directly — it hasn't been produced on this machine yet."
        hint="venv/bin/python modules/m2_automation/main.py"
      />
    );
  }

  return (
    <>
      <Card>
        <SectionLabel>MODULE 2 — RESEARCH RESULTS (CONTROLLED SIMULATION)</SectionLabel>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          Calibrated simulator, 20 seeds, intent uplift 2.5x. This is the
          research measurement, distinct from the live operational view.
        </p>
      </Card>

      <Card className="mt-4">
        <SectionLabel>STRATEGY COMPARISON (SEED 42)</SectionLabel>
        <Table
          rows={data.strategy_comparison}
          columns={[
            { key: "strategy", header: "Strategy" },
            { key: "sends", header: "Sends" },
            { key: "open_rate", header: "Open rate", render: (r) => pct(r.open_rate) },
            { key: "ctr", header: "CTR", render: (r) => pct(r.ctr) },
            { key: "conv_rate", header: "Conv. rate", render: (r) => pct(r.conv_rate) },
            {
              key: "conv_per_1000",
              header: "Conv / 1k sends",
              render: (r) => r.conv_per_1000.toFixed(2),
            },
            {
              key: "days_to_convert",
              header: "Avg days to convert",
              render: (r) => r.days_to_convert.toFixed(2),
            },
            { key: "complexity", header: "Complexity" },
          ]}
        />
      </Card>

      <Card className="mt-4">
        <SectionLabel>20-SEED ROBUSTNESS — MEAN ± STD</SectionLabel>
        <Table
          rows={data.multiseed_summary}
          columns={[
            { key: "strategy", header: "Strategy" },
            {
              key: "conv_per_1k_mean",
              header: "Conv / 1k (mean ± std)",
              render: (r) =>
                `${r.conv_per_1k_mean.toFixed(2)} ± ${r.conv_per_1k_std.toFixed(2)}`,
            },
            {
              key: "conv_rate_mean",
              header: "Conv. rate (mean ± std)",
              render: (r) =>
                `${pct(r.conv_rate_mean)} ± ${pct(r.conv_rate_std)}`,
            },
          ]}
        />
        <Caveat>
          Means and standard deviations across 20 random seeds — the spread
          that separates a real gap between strategies from noise in any one
          run.
        </Caveat>
      </Card>

      <Card className="mt-4">
        <SectionLabel>FIGURES</SectionLabel>
        <div className="mt-3 grid gap-4 md:grid-cols-2">
          {data.figures.map((name) => (
            <figure key={name}>
              <img
                src={`${API_URL}/research/m2/figures/${name}`}
                alt={FIGURE_CAPTIONS[name] ?? name}
                className="w-full rounded-lg border border-slate-200"
              />
              <figcaption className="mt-1 text-xs text-slate-500">
                {FIGURE_CAPTIONS[name] ?? name}
              </figcaption>
            </figure>
          ))}
        </div>
      </Card>

      {data.meta && (
        <Card className="mt-4">
          <SectionLabel>SOURCE</SectionLabel>
          <p className="mt-2 text-sm text-slate-600">{data.meta.source}</p>
          <Caveat>{data.meta.note}</Caveat>
        </Card>
      )}
    </>
  );
}
