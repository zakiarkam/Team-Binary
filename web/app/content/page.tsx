import { PlatformCreditChart } from "@/components/charts";
import {
  BasisBadge,
  Card,
  Caveat,
  EmptyState,
  ErrorState,
  PLATFORM_COLOR,
  PageHeader,
  Pill,
  SectionLabel,
  pct,
} from "@/components/ui";
import type { ContentAsset, ContentPriorities } from "@/lib/api";
import { currentSite, safeGet } from "@/lib/site";

export const dynamic = "force-dynamic";

export default async function ContentPage() {
  const { site, error } = await currentSite();
  if (error) return <ErrorState error={error} />;
  if (!site) {
    return (
      <>
        <PageHeader crumb="Dashboard" title="Content" />
        <EmptyState title="No website registered yet"
                    body="Register a site so its copy can be read." />
      </>
    );
  }

  const [content, priorities] = await Promise.all([
    safeGet<{ assets: ContentAsset[]; count: number }>(
      `/sites/${site.id}/content?limit=24`,
    ),
    safeGet<ContentPriorities>(`/sites/${site.id}/content/priorities`),
  ]);

  const assets = content?.assets ?? [];

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        crumb="Dashboard"
        title="Content"
        subtitle={`Module 4 — platform-native copy written from ${site.url}`}
      />

      <Card className="mb-4">
        <div className="flex items-center justify-between">
          <SectionLabel>WHICH PLATFORMS TO WRITE FOR</SectionLabel>
          <BasisBadge basis={priorities?.data_basis ?? null} />
        </div>
        {priorities?.basis === "none" ? (
          <p className="py-4 text-sm text-slate-500">{priorities.note}</p>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            <PlatformCreditChart ranking={priorities?.platform_ranking ?? {}} />
            <div className="text-sm text-slate-600">
              <p className="mb-2">
                Ranked by <b>{priorities?.basis}</b> over{" "}
                <b>{priorities?.converters ?? 0}</b> converting journeys.
              </p>
              <p className="mb-1 font-semibold text-slate-700">
                Can be written for
              </p>
              <p className="mb-3">
                {Object.keys(priorities?.actionable_ranking ?? {}).join(", ") ||
                  "none"}
              </p>
              <p className="mb-1 font-semibold text-slate-700">
                Acquisition channels only
              </p>
              <p>
                {Object.keys(priorities?.unactionable_channels ?? {}).join(", ") ||
                  "none"}
              </p>
              {priorities?.note && <Caveat>{priorities.note}</Caveat>}
            </div>
          </div>
        )}
      </Card>

      {assets.length === 0 ? (
        <EmptyState
          title="No content generated yet"
          body="Read the website and generate scored, platform-native copy from it."
          hint={`curl -X POST http://localhost:8000/sites/${site.id}/content/generate -H 'Content-Type: application/json' -d '{"engine":"fast"}'`}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {assets.map((a) => (
            <AssetCard key={a.id} asset={a} />
          ))}
        </div>
      )}
    </div>
  );
}

function AssetCard({ asset }: { asset: ContentAsset }) {
  const color = PLATFORM_COLOR[asset.platform] ?? "#334155";
  const tags = Array.isArray(asset.hashtags) ? asset.hashtags : [];

  return (
    <div className="overflow-hidden rounded-2xl bg-white shadow-[0_6px_20px_rgb(15_23_42/0.06)]">
      <div
        className="flex items-center justify-between px-5 py-3 text-sm font-bold text-white"
        style={{ background: color }}
      >
        <span className="capitalize">{asset.platform}</span>
        <span className="rounded-full bg-white/25 px-2.5 py-0.5 text-xs">
          score {asset.final_score?.toFixed(2) ?? "—"}
        </span>
      </div>

      <div className="px-5 py-4">
        {asset.subject && (
          <p className="mb-2 text-sm font-semibold text-slate-800">
            {asset.subject}
          </p>
        )}
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
          {asset.caption}
        </p>
        {tags.length > 0 && (
          <p className="mt-3 text-sm font-medium text-[#3b5bdb]">
            {tags.join(" ")}
          </p>
        )}

        {/* The generator returns caption, hashtags, cta and a creative brief
            per platform. Showing only the first two would hide half of what
            Module 4 produces — and the CTA and the brief are the parts someone
            actually has to act on. */}
        {asset.cta && (
          <div className="mt-4 rounded-lg bg-slate-50 px-3 py-2">
            <p className="text-[0.65rem] font-bold tracking-wide text-slate-400">
              CALL TO ACTION
            </p>
            <p className="mt-0.5 text-sm text-slate-700">{asset.cta}</p>
          </div>
        )}

        {asset.image_prompt && (
          <div className="mt-2 rounded-lg bg-slate-50 px-3 py-2">
            <p className="text-[0.65rem] font-bold tracking-wide text-slate-400">
              {asset.visual_kind === "video" ? "VIDEO BRIEF" : "IMAGE BRIEF"}
            </p>
            <p className="mt-0.5 text-sm italic leading-relaxed text-slate-600">
              {asset.image_prompt}
            </p>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-x-5 gap-y-1 border-t border-slate-100 bg-slate-50 px-5 py-3 text-xs text-slate-500">
        <Metric label="engagement" value={asset.engagement_score} />
        <Metric label="semantic" value={asset.semantic_score} />
        <Metric label="platform fit" value={asset.platform_suitability_score} />
        {asset.campaign_goal && (
          <span>
            <span className="text-slate-400">goal</span> {asset.campaign_goal}
          </span>
        )}
        {asset.tone && (
          <span>
            <span className="text-slate-400">tone</span> {asset.tone}
          </span>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | null }) {
  return (
    <span>
      <span className="text-slate-400">{label}</span>{" "}
      {value == null ? "—" : value.toFixed(2)}
    </span>
  );
}
