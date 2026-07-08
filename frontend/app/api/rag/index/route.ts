export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 600;

const BACKEND = process.env.RAG_BACKEND_URL ?? 'http://localhost:8000';

// Stream the multipart upload straight through to FastAPI without
// buffering the whole file in the Next.js process — keeps the 100MB
// ceiling cheap on memory.
export async function POST(req: Request) {
  const contentType = req.headers.get('content-type') ?? 'multipart/form-data';
  const upstream = await fetch(`${BACKEND}/index`, {
    method: 'POST',
    headers: { 'content-type': contentType },
    body: req.body,
    // @ts-expect-error — Node fetch requires `duplex` when streaming a request body.
    duplex: 'half',
  });
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      'Content-Type': upstream.headers.get('content-type') ?? 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
    },
  });
}
