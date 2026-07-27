export const runtime = 'nodejs';

const BACKEND = process.env.RAG_BACKEND_URL ?? 'http://localhost:8000';

export async function POST(req: Request) {
  const body = await req.text();
  const r = await fetch(`${BACKEND}/learning-draft`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body,
  });
  return new Response(r.body, {
    status: r.status,
    headers: { 'Content-Type': r.headers.get('content-type') ?? 'text/event-stream' },
  });
}
