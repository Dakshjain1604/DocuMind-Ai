export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 600;

const BACKEND = process.env.RAG_BACKEND_URL ?? 'http://localhost:8000';

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const upstream = await fetch(`${BACKEND}/index`, {
      method: 'POST',
      body: formData,
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        'Content-Type': upstream.headers.get('content-type') ?? 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
      },
    });
  } catch (err: any) {
    return new Response(JSON.stringify({ error: err?.message || 'Upload proxy error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
