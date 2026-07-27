export const runtime = "nodejs";

import { proxyJson } from "@/app/api/rag/_lib/proxy";

export async function POST(req: Request) {
  return proxyJson("/compliance-audit", { method: "POST", body: await req.text() });
}
