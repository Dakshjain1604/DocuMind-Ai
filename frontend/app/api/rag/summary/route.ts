export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300;

import { proxyStream } from "@/app/api/rag/_lib/proxy";

export async function POST(req: Request) {
  return proxyStream("/summary", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: await req.text(),
  });
}
