import { NextRequest, NextResponse } from 'next/server';
import bcrypt from 'bcryptjs';
import clientPromise from '../../../../lib/mongodb';

export async function POST(req: NextRequest) {
  try {
    const { email, password } = await req.json();
    if (!email || !password) {
      return NextResponse.json({ message: 'Email and password are required.' }, { status: 400 });
    }
    const client = await clientPromise;
    const db = client.db();
    const users = db.collection('users');
    // Check if user already exists
    const existing = await users.findOne({ email });
    if (existing) {
      return NextResponse.json({ message: 'User already exists.' }, { status: 409 });
    }
    // Hash password
    const hashed = await bcrypt.hash(password, 10);
    // Insert user
    await users.insertOne({ email, password: hashed });
    return NextResponse.json({ message: 'User created successfully.' }, { status: 201 });
  } catch (e) {
    return NextResponse.json({ message: 'Internal server error.' }, { status: 500 });
  }
} 