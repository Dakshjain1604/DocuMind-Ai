import { NextResponse } from "next/server";

import { AUTH_COOKIE } from "@/lib/auth";

/**
 * Clears the session cookie. The dashboard's "Sign Out" control used to be a
 * plain <Link href="/signin">, which navigated away but left the session
 * intact — going back to /Dashboard signed you straight back in.
 */
export async function POST() {
  const res = NextResponse.json({ message: "Signed out." });
  res.cookies.set(AUTH_COOKIE, "", {
    httpOnly: true,
    path: "/",
    maxAge: 0,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
  });
  return res;
}
