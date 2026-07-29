import { AudienceChart, SegmentChart } from "@/components/charts";
import {
  BasisBadge,
  Bar,
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
import type {
  AudienceSummary,
  ReachableAudience,
  Visitor,
} from "@/lib/api";
import { currentSite, safeGet } from "@/lib/site";

export const dynamic = "force-dynamic";

/** Rows per page in the visitor table. */
const PAGE_SIZE = 25;

export default async function AudiencePage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; segment?: string; offset?: string }>;
}) {
  const params = await searchParams;
  const query = params.q?.trim() || undefined;
  const segment = params.segment?.trim() || undefined;
  const offset = Math.max(0, Number(params.offset ?? 0) || 0);

  const { site, error } = await currentSite();
  if (error) return <ErrorState error={error} />;
  if (!site) {
    return (
      <>
        <PageHeader crumb="Dashboard" title="Audience" />
        <EmptyState
          title="No website registered yet"
          body="Register a site and install its snippet — its visitors become your audience."
          hint="venv/bin/python scripts/setup_demo_site.py"
        />
      </>
    );
  }

  const [summary, reach, visitorList] = await Promise.all([
    safeGet<AudienceSummary>(`/sites/${site.id}/audience/summary`),
    safeGet<ReachableAudience>(`/sites/${site.id}/audience/reachable`),
    safeGet<{ visitors: Visitor[]; total: number }>(
      `/sites/${site.id}/visitors?` +
        new URLSearchParams({
          limit: String(PAGE_SIZE),
          offset: String(offset),
          ...(query ? { q: query } : {}),
          ...(segment ? { segment } : {}),
        }),
    ),
  ]);

  const totals = summary?.totals;
  const segments = summary?.segments ?? [];
  const coldStart = segments.reduce((n, s) => n + (s.cold_start ?? 0), 0);

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        crumb="Dashboard"
        title="Audience"
        subtitle={`Visitors of ${site.name}, segmented by Module 1.`}
      />

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="VISITORS" value={totals?.visitors.toLocaleString() ?? "0"}
             hint={`${totals?.new_7d ?? 0} new this week`} />
        <Kpi label="KNOWN" value={totals?.known.toLocaleString() ?? "0"}
             hint="gave us an email" tone="info" />
        <Kpi label="CONTACTABLE" value={totals?.reachable.toLocaleString() ?? "0"}
             hint="explicitly opted in" tone="ok" />
        <Kpi label="COLD START" value={coldStart.toLocaleString()}
             hint="too little history to cluster" tone="accent" />
      </section>

      {reach && (
        <Card className="mt-4">
          <SectionLabel>WHY MOST VISITORS CANNOT BE EMAILED</SectionLabel>
          <div className="mt-3 grid gap-6 md:grid-cols-2">
            <div>
              <Bar label="Anonymous — never gave an address"
                   value={reach.anonymous} max={reach.visitors} color="#94a3b8" />
              <Bar label="Known, but did not opt in"
                   value={reach.known_no_consent} max={reach.visitors} color="#f59e0b" />
              <Bar label="Unsubscribed"
                   value={reach.unsubscribed} max={reach.visitors} color="#dc2626" />
              <Bar label="Contactable"
                   value={reach.reachable} max={reach.visitors} color="#16a34a" />
            </div>
            <div className="text-sm leading-relaxed text-slate-500">
              <p>{reach.explanation}</p>
              <Caveat>
                The gap between <b>{reach.visitors}</b> visitors and{" "}
                <b>{reach.reachable}</b> contactable people is the honest size of
                the addressable audience. Consent is opt-in only and is enforced
                in the database, not just in the interface.
              </Caveat>
            </div>
          </div>
        </Card>
      )}

      <Card className="mt-4">
        <SectionLabel>ACTIVITY — LAST 14 DAYS</SectionLabel>
        <AudienceChart data={summary?.daily ?? []} />
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionLabel>SEGMENTS</SectionLabel>
          <SegmentChart data={segments} />
        </Card>
        <Card>
          <SectionLabel>SEGMENT DETAIL</SectionLabel>
          <Table
            rows={segments}
            columns={[
              { key: "segment_name", header: "Segment" },
              { key: "visitors", header: "Visitors" },
              {
                key: "avg_confidence",
                header: "Confidence",
                render: (r) => (r.avg_confidence ?? 0).toFixed(2),
              },
              {
                key: "cold_start",
                header: "Cold start",
                render: (r) => (r.cold_start ? `${r.cold_start}` : "—"),
              },
            ]}
            empty="Not segmented yet."
          />
          <Caveat>
            Confidence is the level of agreement between the rule, K-Means and
            hierarchical methods — not a probability. Cold-start visitors are
            decided by rules alone, because clustering cannot express
            &ldquo;not enough evidence yet&rdquo;.
          </Caveat>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionLabel>TOP PAGES</SectionLabel>
          <Table
            rows={summary?.top_pages ?? []}
            columns={[
              { key: "path", header: "Path" },
              { key: "views", header: "Views" },
              { key: "visitors", header: "Visitors" },
            ]}
            empty="No page views yet."
          />
        </Card>
        <Card>
          <SectionLabel>ACQUISITION CHANNEL</SectionLabel>
          <Table
            rows={summary?.sources ?? []}
            columns={[
              { key: "source", header: "Source" },
              { key: "visitors", header: "Visitors" },
            ]}
            empty="No traffic yet."
          />
        </Card>
      </div>

      <Card className="mt-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <SectionLabel>
            {segment ? `VISITORS — ${segment.toUpperCase()}` : "VISITORS"}
          </SectionLabel>
          <SearchBox
            action="/audience"
            placeholder="Search email or visitor id"
            value={query}
            hidden={{ segment }}
          />
        </div>
        {query && (
          <p className="mt-2 text-xs text-slate-500">
            {(visitorList?.total ?? 0).toLocaleString()} visitor(s) match{" "}
            <b className="text-slate-700">{query}</b>
          </p>
        )}
        <Table
          rows={visitorList?.visitors ?? []}
          columns={[
            {
              key: "email",
              header: "Visitor",
              render: (v) => (
                <span className="font-medium">
                  {v.email ?? (
                    <span className="text-slate-400">
                      anonymous · {v.visitor_uid.slice(0, 8)}
                    </span>
                  )}
                </span>
              ),
            },
            {
              key: "segment_name",
              header: "Segment",
              render: (v) => (
                <span>
                  {v.segment_name ?? "—"}
                  {v.is_cold_start && (
                    <span className="ml-2 rounded bg-purple-100 px-1.5 py-0.5 text-[0.65rem] font-bold text-purple-700">
                      COLD
                    </span>
                  )}
                </span>
              ),
            },
            { key: "sessions", header: "Sessions" },
            { key: "page_views", header: "Pages" },
            { key: "clicks", header: "Clicks" },
            {
              key: "predicted_conversion",
              header: "Conv. likelihood",
              render: (v) => pct(v.predicted_conversion, 0),
            },
            {
              key: "email_consent",
              header: "Contactable",
              render: (v) => (v.email_consent ? "yes" : "—"),
            },
          ]}
          empty={query ? `Nobody matches "${query}".` : "No visitors tracked yet."}
        />
        <Pagination
          action="/audience"
          total={visitorList?.total ?? 0}
          limit={PAGE_SIZE}
          offset={offset}
          params={{ q: query, segment }}
        />
      </Card>
    </div>
  );
}
