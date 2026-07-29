import { forward } from "@/lib/proxy";

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const body = await req.json().catch(() => ({ executed: true }));
  return forward(`/actions/posts/${id}/executed`, { method: "POST", body });
}
