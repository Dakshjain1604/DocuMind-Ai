import { NextRequest, NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import { SignJWT } from "jose";
import { findUserByEmail } from "@/lib/userStore";
import {
  AUTH_COOKIE,
  JWT_AUDIENCE,
  JWT_ISSUER,
  getJwtSecretKey,
} from "@/lib/auth";

export async function POST(req: NextRequest) {
  try {
    const { email, password } = await req.json();

    if (!email || !password) {
      return NextResponse.json(
        { message: "Email and password are required." },
        { status: 400 }
      );
    }

    const user = await findUserByEmail(email);
    if (!user) {
      return NextResponse.json(
        { message: "Invalid email or password." },
        { status: 401 }
      );
    }

    const isPasswordCorrect = await bcrypt.compare(password, user.password);
    if (!isPasswordCorrect) {
      return NextResponse.json(
        { message: "Invalid email or password." },
        { status: 401 }
      );
    }

    // Issuer/audience are pinned so the backend can reject tokens minted by
    // anything other than this signin flow (see microService/app/core/auth.py).
    const token = await new SignJWT({
      id: user.id,
      email: user.email,
      name: user.name,
    })
      .setProtectedHeader({ alg: "HS256" })
      .setIssuedAt()
      .setExpirationTime("7d")
      .setIssuer(JWT_ISSUER)
      .setAudience(JWT_AUDIENCE)
      .sign(getJwtSecretKey());

    const res = NextResponse.json({
      message: "Signin successful.",
      user: { id: user.id, email: user.email, name: user.name },
    });

    res.cookies.set(AUTH_COOKIE, token, {
      httpOnly: true,
      path: "/",
      maxAge: 60 * 60 * 24 * 7, // 7 days
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
    });

    return res;
  } catch (error: any) {
    console.error("Signin error:", error);
    return NextResponse.json(
      { message: error?.message || "Internal server error during signin." },
      { status: 500 }
    );
  }
}
