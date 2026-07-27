export const runtime = "nodejs";

import { proxyJson } from "@/app/api/rag/_lib/proxy";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ doc_hash: string }> }
) {
  const { doc_hash } = await params;
  return proxyJson(`/graph/${encodeURIComponent(doc_hash)}`, { method: "GET" });
}
