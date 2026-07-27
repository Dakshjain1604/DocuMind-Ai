import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.RAG_BACKEND_URL ?? 'http://localhost:8000';

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ doc_hash: string }> }
) {
  try {
    const { doc_hash } = await params;
    const res = await fetch(`${BACKEND}/documents/${encodeURIComponent(doc_hash)}`, {
      method: "DELETE",
      headers: { "content-type": "application/json" },
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json(
      { success: false, error: err.message || "Failed to delete document" },
      { status: 500 }
    );
  }
}
