export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 300;

const BACKEND = process.env.RAG_BACKEND_URL ?? 'http://localhost:8000';

export async function POST(req: Request) {
  const body = await req.text();
  const upstream = await fetch(`${BACKEND}/summary`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body,
  });
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
