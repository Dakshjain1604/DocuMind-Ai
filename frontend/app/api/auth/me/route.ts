import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import jwt from "jsonwebtoken";

import { AUTH_COOKIE, getJwtSecret } from "@/lib/auth";

/**
 * Who's signed in, from the same cookie middleware.ts already verifies.
 * Nothing in the dashboard chrome ever showed this — the JWT has carried
 * name/email since signin, but the client never had a way to read it back
 * (httpOnly cookies aren't readable from JS by design).
 */
export async function GET() {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }
  try {
    const payload = jwt.verify(token, getJwtSecret()) as { id?: string; email?: string; name?: string };
    return NextResponse.json({ id: payload.id, email: payload.email, name: payload.name });
  } catch {
    return NextResponse.json({ message: "Invalid or expired session." }, { status: 401 });
  }
}
