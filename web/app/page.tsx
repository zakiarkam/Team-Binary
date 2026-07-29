import { AudienceChart, FunnelChart, SegmentChart } from "@/components/charts";
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
  pct,
} from "@/components/ui";
import type {
  AudienceSummary,
  CampaignMetrics,
  ContentAsset,
  FunnelResult,
  ReachableAudience,
} from "@/lib/api";
import { currentSite, safeGet } from "@/lib/site";

export const dynamic = "force-dynamic";

export default async function OverviewPage() {
  const { site, health, error } = await currentSite();
  if (error) return <ErrorState error={error} />;

  if (!site) {
    return (
      <div className="mx-auto max-w-5xl">
        <PageHeader crumb="Dashboard" title="Overview"
                    subtitle="Audience → automation → analytics → content, in one closed loop." />
        <EmptyState
          title="No website registered yet"
          body="Register a website and install its snippet — its visitors become your marketing audience."
          hint="venv/bin/python scripts/setup_demo_site.py"
        />
      </div>
    );
  }

  const [summary, reach, funnel, campaignList, content] = await Promise.all([
    safeGet<AudienceSummary>(`/sites/${site.id}/audience/summary`),
    safeGet<ReachableAudience>(`/sites/${site.id}/audience/reachable`),
    safeGet<FunnelResult>(`/sites/${site.id}/analytics/funnel`),
    safeGet<{ campaigns: CampaignMetrics[] }>(`/sites/${site.id}/campaigns`),
    safeGet<{ assets: ContentAsset[]; count: number }>(
      `/sites/${site.id}/content?limit=3`,
    ),
  ]);

  const totals = summary?.totals;
  const campaigns = campaignList?.campaigns ?? [];
  const best = campaigns.length
    ? campaigns.reduce((a, b) =>
        b.conversions_per_1000_sends > a.conversions_per_1000_sends ? b : a,
      )
    : null;

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        crumb="Dashboard"
        title="Overview"
        subtitle="Audience → automation → analytics → content, in one closed loop."
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <Pill tone={health?.database === "up" ? "ok" : "bad"}>
          database {health?.database ?? "unknown"}
        </Pill>
        <Pill tone={health?.email_delivery === "live" ? "ok" : "warn"}>
          email {health?.email_delivery === "live" ? "live" : "dry run"}
        </Pill>
        <span className="text-sm text-slate-500">
          tracking <b className="text-slate-700">{site.name}</b> · {site.url}
        </span>
      </div>

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="VISITORS" value={totals?.visitors.toLocaleString() ?? "0"}
             hint={`${totals?.new_7d ?? 0} new this week`} />
        <Kpi label="CONTACTABLE" value={reach?.reachable.toLocaleString() ?? "0"}
             hint="explicitly opted in" tone="ok" />
        <Kpi label="CONVERSIONS"
             value={(funnel?.funnel.convert ?? 0).toLocaleString()}
             hint="from tracked campaigns" tone="accent" />
        <Kpi label="CONTENT ASSETS" value={content?.count ?? 0}
             hint="scored and stored" tone="warn" />
      </section>

      <Card className="mt-4">
        <SectionLabel>AUDIENCE — LAST 14 DAYS</SectionLabel>
        <AudienceChart data={summary?.daily ?? []} />
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionLabel>SEGMENTS</SectionLabel>
          <SegmentChart data={summary?.segments ?? []} />
        </Card>
        <Card>
          <div className="flex items-center justify-between">
            <SectionLabel>CAMPAIGN FUNNEL</SectionLabel>
            <BasisBadge basis={funnel?.data_basis ?? null} />
          </div>
          <FunnelChart
            funnel={funnel?.funnel ?? { sent: 0, open: 0, click: 0, convert: 0 }}
          />
        </Card>
      </div>

      {best && (
        <Card className="mt-4">
          <SectionLabel>BEST-PERFORMING AUTOMATION STRATEGY</SectionLabel>
          <div className="mt-2 flex flex-wrap items-baseline gap-x-6 gap-y-2">
            <span className="text-2xl font-extrabold capitalize text-ok">
              {best.strategy}
            </span>
            <span className="text-sm text-slate-600">
              {best.conversions_per_1000_sends.toFixed(1)} conversions per 1,000
              sends
            </span>
            <span className="text-sm text-slate-600">
              CTR {pct(best.click_through_rate)}
            </span>
            <span className="text-sm text-slate-600">
              {best.operational_complexity} decision rules
            </span>
          </div>
          <Caveat>
            Ranked by conversions per 1,000 sends rather than raw conversions: a
            fixed workflow can win on volume simply by sending far more mail.
            Operational complexity is shown beside it, because a policy that wins
            narrowly while needing eight rules instead of one is not obviously
            better.
          </Caveat>
        </Card>
      )}

      {content?.assets?.length ? (
        <Card className="mt-4">
          <SectionLabel>LATEST GENERATED CONTENT</SectionLabel>
          <div className="mt-3 space-y-3">
            {content.assets.map((a) => (
              <div key={a.id} className="rounded-xl border border-slate-200 p-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold uppercase tracking-wide text-slate-500">
                    {a.platform}
                  </span>
                  <span className="text-slate-400">
                    score {a.final_score?.toFixed(2) ?? "—"}
                  </span>
                </div>
                <p className="mt-1 line-clamp-2 text-sm text-slate-700">
                  {a.caption}
                </p>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
    </div>
  );
}
