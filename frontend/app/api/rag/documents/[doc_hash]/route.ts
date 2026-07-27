import { NextRequest, NextResponse } from "next/server";

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ doc_hash: string }> }
) {
  try {
    const { doc_hash } = await params;
    const res = await fetch(`http://127.0.0.1:8000/documents/${doc_hash}`, {
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
