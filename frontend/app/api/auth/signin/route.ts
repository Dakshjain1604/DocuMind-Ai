import { NextRequest, NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import { findUserByEmail } from "@/lib/userStore";
import { AUTH_COOKIE, getJwtSecret } from "@/lib/auth";

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

    const token = jwt.sign(
      { id: user.id, email: user.email, name: user.name },
      getJwtSecret(),
      { expiresIn: "7d" }
    );

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
