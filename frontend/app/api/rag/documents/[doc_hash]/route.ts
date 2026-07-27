export const runtime = "nodejs";

import { proxyJson } from "@/app/api/rag/_lib/proxy";

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ doc_hash: string }> }
) {
  const { doc_hash } = await params;
  return proxyJson(`/documents/${encodeURIComponent(doc_hash)}`, { method: "DELETE" });
}
