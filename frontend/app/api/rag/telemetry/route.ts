import { NextResponse } from "next/server";

export async function GET() {
  try {
    const res = await fetch("http://127.0.0.1:8000/telemetry/stats", {
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
