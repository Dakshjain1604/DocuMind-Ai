import { NextResponse } from "next/server";

const BACKEND = process.env.RAG_BACKEND_URL ?? 'http://localhost:8000';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/telemetry/stats`, {
      method: "GET",
      headers: { "content-type": "application/json" },
      cache: "no-store",
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json(
      { success: false, error: err.message || "Failed to fetch telemetry stats" },
      { status: 500 }
    );
  }
}
