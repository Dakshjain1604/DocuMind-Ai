import { NextRequest, NextResponse } from "next/server";
import { jwtVerify } from "jose";

import {
  AUTH_COOKIE,
  JWT_AUDIENCE,
  JWT_ISSUER,
  getJwtSecretKey,
} from "@/lib/auth";

/**
 * Gate for authenticated pages.
 *
 * Before this existed, the signin route issued a JWT, set it as a cookie, and
 * nothing ever read it back — /Dashboard was reachable by anyone, and the
 * "Sign Out" button was a plain link that left the cookie in place. Auth was
 * decorative.
 *
 * Runs on the Edge runtime, which is why verification uses `jose` rather than
 * `jsonwebtoken` (the latter depends on Node crypto and will not load here).
 */
export async function middleware(req: NextRequest) {
  const token = req.cookies.get(AUTH_COOKIE)?.value;

  const isApiRequest = req.nextUrl.pathname.startsWith("/api/rag/");

  const reject = () => {
    if (isApiRequest) {
      // Defense-in-depth for the ownership-sensitive routes. The backend
      // already rejects these without a valid bearer token; this keeps the
      // client from even seeing a redirection to an HTML login page.
      return new NextResponse(
        JSON.stringify({
          success: false,
          error: { code: "unauthorized", message: "Authentication required." },
          data: {},
        }),
        { status: 401, headers: { "Content-Type": "application/json" } }
      );
    }
    const url = new URL("/signin", req.url);
    // Preserve where the user was headed so signin can send them back.
    url.searchParams.set("next", req.nextUrl.pathname);
    const res = NextResponse.redirect(url);
    res.cookies.delete(AUTH_COOKIE); // clear anything expired or malformed
    return res;
  };

  if (!token) return reject();

  try {
    await jwtVerify(token, getJwtSecretKey(), {
      issuer: JWT_ISSUER,
      audience: JWT_AUDIENCE,
    });
    return NextResponse.next();
  } catch {
    return reject();
  }
}

export const config = {
  matcher: [
    "/Dashboard/:path*",
    "/api/rag/documents/:path*",
    "/api/rag/graph/:path*",
    "/api/rag/trace/:path*",
  ],
};
