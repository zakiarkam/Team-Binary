import { AttributionChart, FunnelChart } from "@/components/charts";
import {
  BasisBadge,
  Card,
  Caveat,
  EmptyState,
  ErrorState,
  Kpi,
  PageHeader,
  SectionLabel,
  Table,
  pct,
} from "@/components/ui";
import type {
  AttributionResult,
  FunnelResult,
  Recommendation,
} from "@/lib/api";
import { currentSite, safeGet } from "@/lib/site";

export const dynamic = "force-dynamic";

export default async function AnalyticsPage() {
  const { site, error } = await currentSite();
  if (error) return <ErrorState error={error} />;
  if (!site) {
    return (
      <>
        <PageHeader crumb="Dashboard" title="Analytics" />
        <EmptyState title="No website registered yet"
                    body="Register a site and run a campaign first." />
      </>
    );
  }

  const [funnel, attribution, recs] = await Promise.all([
    safeGet<FunnelResult>(`/sites/${site.id}/analytics/funnel`),
    safeGet<AttributionResult>(`/sites/${site.id}/analytics/attribution`),
    safeGet<{ recommendations: Recommendation[]; mix: { recommendation: string; visitors: number }[]; note: string }>(
      `/sites/${site.id}/analytics/recommendations?limit=15`,
    ),
  ]);

  const f = funnel?.funnel;
  const hasCampaign = (f?.sent ?? 0) > 0;
  const diag = attribution?.diagnostics ?? {};

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        crumb="Dashboard"
        title="Analytics"
        subtitle="Module 3 — funnel, attribution and prediction over observed data."
      />

      {!hasCampaign ? (
        <EmptyState
          title="No campaign data yet"
          body="Analytics reads the funnel that campaigns produce. Send one first."
          hint="venv/bin/python scripts/run_strategy_comparison.py --site-id 1 --reset --simulate-engagement"
        />
      ) : (
        <>
          <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Kpi label="SENT" value={f!.sent.toLocaleString()} />
            <Kpi label="OPENED" value={f!.open.toLocaleString()} tone="info" />
            <Kpi label="CLICKED" value={f!.click.toLocaleString()} tone="warn" />
            <Kpi label="CONVERTED" value={f!.convert.toLocaleString()} tone="ok" />
          </section>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Card>
              <div className="flex items-center justify-between">
                <SectionLabel>CAMPAIGN FUNNEL</SectionLabel>
                <BasisBadge basis={funnel!.data_basis} />
              </div>
              <FunnelChart funnel={f!} />
              {funnel?.caveat && <Caveat>{funnel.caveat}</Caveat>}
            </Card>

            <Card>
              <SectionLabel>WHERE PEOPLE ARE LOST</SectionLabel>
              <div className="mt-3 space-y-3">
                {Object.entries(funnel?.dropoffs ?? {}).map(([stage, rate]) => (
                  <div key={stage}>
                    <div className="mb-1 flex justify-between text-sm">
                      <span className="text-slate-600">{stage}</span>
                      <span className="font-semibold text-slate-700">
                        {pct(rate, 0)} lost
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-red-400"
                           style={{ width: `${Math.min(100, rate * 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <Caveat>
                A high sent→open loss usually means blocked images rather than an
                unread message. The click→convert step is the one that reflects
                real intent.
              </Caveat>
            </Card>
          </div>

          <Card className="mt-4">
            <div className="flex items-center justify-between">
              <SectionLabel>ATTRIBUTION — FOUR MODELS, SAME JOURNEYS</SectionLabel>
              <BasisBadge basis={attribution?.data_basis ?? null} />
            </div>
            {attribution?.note ? (
              <p className="py-6 text-sm text-slate-500">{attribution.note}</p>
            ) : (
              <>
                <AttributionChart models={attribution?.models ?? {}} />
                <div className="mt-3 grid gap-4 text-sm text-slate-600 md:grid-cols-2">
                  <p>
                    <b>{attribution?.converters ?? 0}</b> converting journeys,
                    averaging{" "}
                    <b>{diag.mean_distinct_touchpoints ?? "—"}</b> distinct
                    platforms each.
                  </p>
                  <p>
                    <b>{pct(diag.single_touch_share, 0)}</b> of journeys had a
                    single touchpoint.
                  </p>
                </div>
                {diag.note && <Caveat>{diag.note}</Caveat>}
                <Caveat>
                  First-touch credits the channel that brought someone in;
                  last-touch credits whatever closed. Where they point at
                  different platforms, that disagreement is the finding — a
                  single-touch model would attribute the whole conversion to one
                  end of the journey.
                </Caveat>
              </>
            )}
          </Card>

          {funnel?.by_strategy && funnel.by_strategy.length > 0 && (
            <Card className="mt-4">
              <SectionLabel>FUNNEL BY AUTOMATION STRATEGY</SectionLabel>
              <Table
                rows={funnel.by_strategy}
                columns={[
                  { key: "strategy", header: "Strategy" },
                  { key: "sent", header: "Sent" },
                  { key: "open", header: "Opened" },
                  { key: "click", header: "Clicked" },
                  { key: "convert", header: "Converted" },
                ]}
              />
            </Card>
          )}

          <Card className="mt-4">
            <SectionLabel>NEXT-BEST ACTION PER VISITOR</SectionLabel>
            <div className="mt-2 mb-3 flex flex-wrap gap-4 text-sm text-slate-600">
              {(recs?.mix ?? []).map((m) => (
                <span key={m.recommendation}>
                  <b className="text-slate-800">{m.visitors}</b>{" "}
                  {m.recommendation.replace(/_/g, " ")}
                </span>
              ))}
            </div>
            <Table
              rows={recs?.recommendations ?? []}
              columns={[
                {
                  key: "email",
                  header: "Visitor",
                  render: (r) => (
                    <span>
                      {r.email ?? `#${r.visitor_id}`}
                      {r.is_synthetic && (
                        <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[0.65rem] font-bold text-amber-700">
                          SIM
                        </span>
                      )}
                    </span>
                  ),
                },
                { key: "segment_name", header: "Segment" },
                {
                  key: "predicted_conversion",
                  header: "Conv. likelihood",
                  render: (r) => pct(r.predicted_conversion, 0),
                },
                {
                  key: "drop_off_risk",
                  header: "Drop-off risk",
                  render: (r) => pct(r.drop_off_risk, 0),
                },
                {
                  key: "recommendation",
                  header: "Next best action",
                  render: (r) => r.recommendation.replace(/_/g, " "),
                },
              ]}
              empty="No predictions yet — run analytics."
            />
            {recs?.note && <Caveat>{recs.note}</Caveat>}
          </Card>
        </>
      )}
    </div>
  );
}
