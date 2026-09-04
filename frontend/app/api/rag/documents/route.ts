export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { proxyJson } from "@/app/api/rag/_lib/proxy";

export async function GET() {
  return proxyJson("/documents", { method: "GET" });
}
