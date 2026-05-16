export const runtime = 'nodejs';

const BACKEND = process.env.RAG_BACKEND_URL ?? 'http://localhost:8000';

export async function POST(req: Request) {
  const form = await req.formData();
  const upstream = await fetch(`${BACKEND}/index`, { method: 'POST', body: form });
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      'Content-Type': upstream.headers.get('content-type') ?? 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
    },
  });
}
