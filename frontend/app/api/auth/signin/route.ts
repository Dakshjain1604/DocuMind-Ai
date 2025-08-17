// app/api/auth/signin/route.ts
import { NextRequest, NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import { connectToMongoDB } from "@/lib/mongodb";
import User from "@/models/userModel"; 
const JWT_SECRET=process.env.JWT_SECRET || "changeme";
export async function POST(req: NextRequest) {
  await connectToMongoDB();

  try {
    const { email, password } = await req.json();
    console.log(email,password)
    if (!email || !password) {
      return NextResponse.json(
        { message: "Email and password are required." },
        { status: 400 }
      );
    }

    const user = await User.findOne({ email });
    console.log(user)
    if (!user) {
      return NextResponse.json(
        { message: "Invalid credentials." },
        { status: 401 }
      );
    }

    const isPasswordCorrect = await bcrypt.compare(password, user.password);

    if (!isPasswordCorrect) {
      return NextResponse.json(
        { message: "Invalid credentials." },
        { status: 401 }
      );
    }

    const token = jwt.sign({ id: user._id, email: user.email }, JWT_SECRET, {
      expiresIn: "7d",
    });

    const res = NextResponse.json({ message: "Signin successful." });
    res.cookies.set("token", token, {
      httpOnly: true,
      path: "/",
      maxAge: 60 * 60 * 1 , // 1 hour
      secure: true,
      sameSite: "none",
    });
    return res;
  } catch (error) {
    console.error("Signin error:", error);
    return NextResponse.json(
      { message: "Internal server error." },
      { status: 500 }
    );
  }
}
