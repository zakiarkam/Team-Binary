import { forward } from "@/lib/proxy";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ campaignId: string; step: string }> },
) {
  const { campaignId, step } = await params;
  return forward(`/actions/emails/${campaignId}/${step}/recipients`, {
    method: "GET",
  });
}
