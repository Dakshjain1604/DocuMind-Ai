export const runtime = "nodejs";

import { proxyJson } from "@/app/api/rag/_lib/proxy";

export async function POST(req: Request) {
  return proxyJson("/audio-briefing", { method: "POST", body: await req.text() });
}
