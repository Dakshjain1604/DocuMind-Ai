export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 600;

import { proxyStream } from "@/app/api/rag/_lib/proxy";

export async function POST(req: Request) {
  // Pass the request body straight through rather than await req.formData(),
  // which buffered the whole upload (up to 5 x 100MB) into Node's memory before
  // forwarding a single byte. The content-type header carries the multipart
  // boundary, so it has to be forwarded with it.
  const contentType = req.headers.get("content-type");
  return proxyStream("/index", {
    method: "POST",
    headers: contentType ? { "content-type": contentType } : undefined,
    body: req.body ?? undefined,
  });
}
