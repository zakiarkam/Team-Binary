import { AttributionChart, FunnelChart } from "@/components/charts";
import {
  BasisBadge,
  Card,
  Caveat,
  EmptyState,
  ErrorState,
  Kpi,
  PageHeader,
  Pagination,
  SearchBox,
  SectionLabel,
  Table,
  pct,
} from "@/components/ui";
import { ModuleResearch, ViewTabs } from "@/components/research";
import type {
  AttributionResult,
  FunnelResult,
  ModuleResearchResult,
  Recommendation,
} from "@/lib/api";
import { currentSite, safeGet } from "@/lib/site";

export const dynamic = "force-dynamic";

/** Rows per page in the per-customer prediction table. */
const PAGE_SIZE = 25;

/** Module 3's experiments in the research layer: E4, E5, E8, E9, E11. */
const MODULE = 3;

export default async function AnalyticsPage({
  searchParams,
}: {
  searchParams: Promise<{
    q?: string;
    segment?: string;
    offset?: string;
    view?: string;
  }>;
}) {
  const params = await searchParams;
  const query = params.q?.trim() || undefined;
  const segment = params.segment?.trim() || undefined;
  const offset = Math.max(0, Number(params.offset ?? 0) || 0);
  const view = params.view === "research" ? "research" : "live";

  // Before the site lookup: the research tab reads the experiment layer's
  // result files, not the database, so it renders without a registered site.
  if (view === "research") {
    const research = await safeGet<ModuleResearchResult>(
      `/research/modules/${MODULE}/results`,
    );
    return (
      <div className="mx-auto max-w-6xl">
        <PageHeader
          crumb="Dashboard"
          title="Analytics"
          subtitle="Module 3 — attribution, prediction, uplift and off-policy evaluation."
        />
        <ViewTabs view={view} />
        <ModuleResearch data={research} module={MODULE} />
      </div>
    );
  }

  const { site, error } = await currentSite();
  if (error) return <ErrorState error={error} />;
  if (!site) {
    return (
      <>
        <PageHeader crumb="Dashboard" title="Analytics" />
        <EmptyState
          title="No website registered yet"
          body="Register a site and run a campaign first."
        />
      </>
    );
  }

  const [funnel, attribution, recs] = await Promise.all([
    safeGet<FunnelResult>(`/sites/${site.id}/analytics/funnel`),
    safeGet<AttributionResult>(`/sites/${site.id}/analytics/attribution`),
    safeGet<{
      recommendations: Recommendation[];
      mix: { recommendation: string; visitors: number }[];
      total: number;
      note: string;
    }>(
      `/sites/${site.id}/analytics/recommendations?` +
        new URLSearchParams({
          limit: String(PAGE_SIZE),
          offset: String(offset),
          ...(query ? { q: query } : {}),
          ...(segment ? { segment } : {}),
        }),
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

      <ViewTabs view={view} />

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
            <Kpi
              label="CLICKED"
              value={f!.click.toLocaleString()}
              tone="warn"
            />
            <Kpi
              label="CONVERTED"
              value={f!.convert.toLocaleString()}
              tone="ok"
            />
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
                      <div
                        className="h-full rounded-full bg-red-400"
                        style={{ width: `${Math.min(100, rate * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <Caveat>
                A high sent→open loss usually means blocked images rather than
                an unread message. The click→convert step is the one that
                reflects real intent.
              </Caveat>
            </Card>
          </div>

          <Card className="mt-4">
            <div className="flex items-center justify-between">
              <SectionLabel>
                ATTRIBUTION — FOUR MODELS, SAME JOURNEYS
              </SectionLabel>
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
                    averaging <b>{diag.mean_distinct_touchpoints ?? "—"}</b>{" "}
                    distinct platforms each.
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
            <div className="flex flex-wrap items-center justify-between gap-3">
              <SectionLabel>
                {segment
                  ? `NEXT-BEST ACTION — ${segment.toUpperCase()}`
                  : "NEXT-BEST ACTION PER CUSTOMER"}
              </SectionLabel>
              <SearchBox
                action="/dashboard/analytics"
                placeholder="Search email or visitor id"
                value={query}
                hidden={{ segment }}
              />
            </div>
            {/* The mix counts the whole audience, not the current page — it is
                a breakdown of everyone scored, and paging must not change it. */}
            <div className="mt-2 mb-3 flex flex-wrap gap-4 text-sm text-slate-600">
              {(recs?.mix ?? []).map((m) => (
                <span key={m.recommendation}>
                  <b className="text-slate-800">
                    {m.visitors.toLocaleString()}
                  </b>{" "}
                  {m.recommendation.replace(/_/g, " ")}
                </span>
              ))}
            </div>
            <Table
              rows={recs?.recommendations ?? []}
              columns={[
                {
                  // The order of this table is itself the result, so the
                  // position is worth stating. It comes from the API rather
                  // than the row index: this table is searchable and paged, and
                  // a counted row would tell someone who searched for one
                  // customer that they are the top prospect.
                  key: "rank",
                  header: "#",
                  render: (r) => (
                    <span className="font-mono text-xs tabular-nums text-slate-400">
                      {r.rank}
                    </span>
                  ),
                },
                {
                  key: "email",
                  header: "Visitor",
                  render: (r) => (
                    <span>
                      {r.email ?? `#${r.visitor_id}`}
                      {r.source === "dataset" && (
                        <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-[0.65rem] font-bold text-slate-600">
                          DATASET
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
              empty={
                query
                  ? `Nobody matches "${query}".`
                  : "No predictions yet — run analytics."
              }
            />
            <Pagination
              action="/dashboard/analytics"
              total={recs?.total ?? 0}
              limit={PAGE_SIZE}
              offset={offset}
              params={{ q: query, segment }}
            />
            {recs?.note && <Caveat>{recs.note}</Caveat>}
          </Card>
        </>
      )}
    </div>
  );
}
