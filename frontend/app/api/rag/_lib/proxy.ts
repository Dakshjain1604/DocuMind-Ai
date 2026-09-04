/**
 * Shared proxy to the Python RAG service.
 *
 * The 14 route handlers under app/api/rag/ each reimplemented this, and did so
 * inconsistently: six hardcoded 127.0.0.1 while eight read the env var, seven
 * had no try/catch at all (so a downed backend produced Next's HTML 500, the
 * client's r.json() threw, and the panel stayed blank forever), none set a
 * timeout, and only some SSE routes sent the no-buffering headers.
 *
 * The `_lib` prefix keeps this directory out of the App Router's route table.
 */

const BACKEND = process.env.RAG_BACKEND_URL ?? "http://localhost:8000";

/** JSON requests should fail fast; generation can legitimately take a while. */
const JSON_TIMEOUT_MS = 120_000;

/** Headers that keep an SSE stream from being buffered by an intermediary. */
const STREAM_HEADERS = {
  "Content-Type": "text/event-stream",
  "Cache-Control": "no-cache, no-transform",
  Connection: "keep-alive",
  "X-Accel-Buffering": "no",
} as const;

function errorResponse(message: string, status = 502): Response {
  // Same envelope the backend uses, so clients have exactly one shape to read.
  return new Response(
    JSON.stringify({
      success: false,
      error: { code: "backend_unreachable", message },
      data: {},
    }),
    { status, headers: { "Content-Type": "application/json" } }
  );
}

function describe(err: unknown): string {
  if (err instanceof DOMException && err.name === "TimeoutError") {
    return "The document service did not respond in time.";
  }
  if (err instanceof Error && err.message.includes("ECONNREFUSED")) {
    return "Could not reach the document service. Is the backend running?";
  }
  return "Could not reach the document service.";
}

import { cookies } from "next/headers";
import { AUTH_COOKIE } from "@/lib/auth";

async function getAuthHeader(): Promise<Record<string, string>> {
  const cookieStore = await cookies();
  // Same cookie name middleware.ts and the auth routes use — hardcoding
  // "token" here would drift silently if AUTH_COOKIE ever changes.
  const token = cookieStore.get(AUTH_COOKIE)?.value;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Proxy a JSON request/response pair. */
export async function proxyJson(
  path: string,
  init: { method: string; body?: string } = { method: "GET" }
): Promise<Response> {
  try {
    const authHeader = await getAuthHeader();
    const upstream = await fetch(`${BACKEND}${path}`, {
      method: init.method,
      headers: { "content-type": "application/json", ...authHeader },
      body: init.body,
      cache: "no-store",
      signal: AbortSignal.timeout(JSON_TIMEOUT_MS),
    });
    return new Response(await upstream.text(), {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") ?? "application/json",
      },
    });
  } catch (err) {
    return errorResponse(describe(err));
  }
}

/** Proxy an SSE stream, passing the upstream body straight through. */
export async function proxyStream(
  path: string,
  init: { method: string; body?: BodyInit; headers?: HeadersInit }
): Promise<Response> {
  try {
    const authHeader = await getAuthHeader();
    const upstream = await fetch(`${BACKEND}${path}`, {
      method: init.method,
      headers: { ...init.headers, ...authHeader } as HeadersInit,
      body: init.body,
      // No timeout: these stream for as long as generation takes. The client
      // aborting propagates and closes the upstream connection.
      // @ts-expect-error -- duplex is required by Node's fetch for a stream body
      duplex: "half",
    });

    // An upstream failure is JSON, not SSE. Labelling it text/event-stream (as
    // the previous handlers did unconditionally) meant the client's frame
    // parser found no `event:` line and reported nothing at all.
    if (!upstream.ok) {
      return new Response(await upstream.text(), {
        status: upstream.status,
        headers: {
          "Content-Type": upstream.headers.get("content-type") ?? "application/json",
        },
      });
    }

    const headers: Record<string, string> = { ...STREAM_HEADERS };
    const requestId = upstream.headers.get("x-request-id");
    if (requestId) headers["X-Request-Id"] = requestId;

    return new Response(upstream.body, { status: upstream.status, headers });
  } catch (err) {
    return errorResponse(describe(err));
  }
}
