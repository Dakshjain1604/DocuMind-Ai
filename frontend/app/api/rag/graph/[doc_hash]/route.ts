export const runtime = 'nodejs';

const BACKEND = process.env.RAG_BACKEND_URL ?? 'http://localhost:8000';

export async function GET(_req: Request, { params }: { params: Promise<{ doc_hash: string }> }) {
  const { doc_hash } = await params;
  const r = await fetch(`${BACKEND}/graph/${encodeURIComponent(doc_hash)}`);
  return new Response(await r.text(), {
    status: r.status,
    headers: { 'Content-Type': r.headers.get('content-type') ?? 'application/json' },
  });
}
