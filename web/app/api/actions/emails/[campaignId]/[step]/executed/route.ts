import { forward } from "@/lib/proxy";

export async function POST(
  req: Request,
  { params }: { params: Promise<{ campaignId: string; step: string }> },
) {
  const { campaignId, step } = await params;
  const body = await req.json().catch(() => ({ executed: true }));
  return forward(`/actions/emails/${campaignId}/${step}/executed`, {
    method: "POST",
    body,
  });
}
