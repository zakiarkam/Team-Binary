import {
  ActionPlan,
  GeneratePlanButton,
  type PlanAction,
} from "@/components/ActionPlan";
import { Card, ErrorState, Kpi, PageHeader } from "@/components/ui";
import { currentSite, safeGet } from "@/lib/site";

export const dynamic = "force-dynamic";

interface Plan {
  actions: PlanAction[];
  counts: { email: number; post: number; total: number };
  how_to_use: string;
}

export default async function PlanPage() {
  const { site, error } = await currentSite();
  if (error) return <ErrorState error={error} />;
  if (!site) return null; // currentSite redirects to onboarding

  const plan = await safeGet<Plan>(`/sites/${site.id}/plan`);
  const actions = plan?.actions ?? [];

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        crumb="Dashboard"
        title="Action Plan"
        subtitle="What to do next for this website — with the content already written."
      />

      <Card className="mb-4">
        <p className="text-sm leading-relaxed text-slate-600">
          <b className="text-slate-800">This platform advises, it does not publish.</b>{" "}
          Every action below is yours to execute in your own email tool or
          social account. Keep the tracked links exactly as they are — that is
          how clicks and conversions still reach your analytics after you post.
        </p>
      </Card>

      <section className="mb-4 grid grid-cols-3 gap-4">
        <Kpi label="ACTIONS WAITING" value={plan?.counts.total ?? 0} />
        <Kpi label="EMAILS TO SEND" value={plan?.counts.email ?? 0} tone="brand" />
        <Kpi label="POSTS TO PUBLISH" value={plan?.counts.post ?? 0} tone="accent" />
      </section>

      <GeneratePlanButton siteId={site.id} />

      <ActionPlan actions={actions} />
    </div>
  );
}
