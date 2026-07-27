import { NextRequest, NextResponse } from "next/server";
import { jwtVerify } from "jose";

import { AUTH_COOKIE, getJwtSecretKey } from "@/lib/auth";

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

  const redirectToSignin = () => {
    const url = new URL("/signin", req.url);
    // Preserve where the user was headed so signin can send them back.
    url.searchParams.set("next", req.nextUrl.pathname);
    const res = NextResponse.redirect(url);
    res.cookies.delete(AUTH_COOKIE); // clear anything expired or malformed
    return res;
  };

  if (!token) return redirectToSignin();

  try {
    await jwtVerify(token, getJwtSecretKey());
    return NextResponse.next();
  } catch {
    return redirectToSignin();
  }
}

export const config = {
  matcher: ["/Dashboard/:path*"],
};
