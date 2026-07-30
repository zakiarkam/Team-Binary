import {
  ActionPlan,
  GeneratePlanButton,
  type DoneAction,
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

interface PlanHistory {
  history: DoneAction[];
  counts: { email: number; post: number; executed: number; skipped: number;
            total: number };
  note: string;
}

export default async function PlanPage() {
  const { site, error } = await currentSite();
  if (error) return <ErrorState error={error} />;
  if (!site) return null; // currentSite redirects to onboarding

  // Outstanding work and finished work are separate reads: the plan endpoint
  // shows only what is still waiting, which is what makes "what did I already
  // send?" a question the history has to answer.
  const [plan, done] = await Promise.all([
    safeGet<Plan>(`/sites/${site.id}/plan`),
    safeGet<PlanHistory>(`/sites/${site.id}/plan/history`),
  ]);
  const actions = plan?.actions ?? [];
  const history = done?.history ?? [];

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        crumb="Dashboard"
        title="Action Plan"
        subtitle="What to do next for this website — with the content already written."
      />

      <Card className="mb-4">
        <p className="text-sm leading-relaxed text-slate-600">
          <b className="text-slate-800">
            This platform advises, it does not publish.
          </b>{" "}
          Every action below is yours to execute in your own email tool or
          social account. Keep the tracked links exactly — as they are that is how
          clicks and conversions still reach your analytics after you post.
        </p>
      </Card>

      <section className="mb-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="ACTIONS WAITING" value={plan?.counts.total ?? 0} />
        <Kpi
          label="EMAILS TO SEND"
          value={plan?.counts.email ?? 0}
          tone="brand"
        />
        <Kpi
          label="POSTS TO PUBLISH"
          value={plan?.counts.post ?? 0}
          tone="accent"
        />
        <Kpi
          label="ALREADY DONE"
          value={done?.counts.executed ?? 0}
          tone="ok"
        />
      </section>

      <GeneratePlanButton siteId={site.id} />

      <ActionPlan
        actions={actions}
        history={history}
        historyNote={done?.note}
      />
    </div>
  );
}
