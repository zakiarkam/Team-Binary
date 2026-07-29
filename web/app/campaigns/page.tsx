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
import type { CampaignMetrics, ReachableAudience } from "@/lib/api";
import { currentSite, safeGet } from "@/lib/site";

export const dynamic = "force-dynamic";

const STRATEGY_BLURB: Record<string, string> = {
  fixed: "Everyone gets the same sequence on the same schedule.",
  trigger: "Only the opener is scheduled; what follows depends on behaviour.",
  hybrid: "A fixed backbone, adjusted by segment and predicted conversion.",
};

export default async function CampaignsPage() {
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
