import fs from "fs";
import path from "path";
import bcrypt from "bcryptjs";
import mongoose, { Schema, type Document, models } from "mongoose";
import { connectToMongoDB } from "./mongodb";

export interface UserAccount {
  id: string;
  name: string;
  email: string;
  password: string;
  createdAt: string;
}

// Document shape for the Mongo branch, folded in from the old models/userModel.ts
// — userStore was its only consumer, so the split bought indirection for nothing.
interface UserDoc extends Document {
  name: string;
  email: string;
  password: string;
  createdAt: Date;
}

const UserSchema = new Schema<UserDoc>({
  name: { type: String, required: true },
  email: { type: String, required: true, unique: true },
  password: { type: String, required: true },
  createdAt: { type: Date, default: Date.now },
});

// Reuse an existing model across hot reloads (Next.js dev re-imports modules).
const User = (models.User || mongoose.model<UserDoc>("User", UserSchema)) as typeof mongoose.Model<UserDoc>;

const LOCAL_USERS_FILE = path.join(process.cwd(), "..", "tmp", "users_db.json");

function ensureLocalFile() {
  const dir = path.dirname(LOCAL_USERS_FILE);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  if (!fs.existsSync(LOCAL_USERS_FILE)) {
    fs.writeFileSync(LOCAL_USERS_FILE, JSON.stringify([]), "utf-8");
  }
}

function getLocalUsers(): UserAccount[] {
  try {
    ensureLocalFile();
    const raw = fs.readFileSync(LOCAL_USERS_FILE, "utf-8");
    return JSON.parse(raw || "[]");
  } catch (err) {
    console.error("Error reading local user file store:", err);
    return [];
  }
}

function saveLocalUsers(users: UserAccount[]) {
  try {
    ensureLocalFile();
    fs.writeFileSync(LOCAL_USERS_FILE, JSON.stringify(users, null, 2), "utf-8");
  } catch (err) {
    console.error("Error writing local user file store:", err);
  }
}

export async function findUserByEmail(email: string): Promise<UserAccount | null> {
  const normalizedEmail = email.toLowerCase().trim();

  // Try MongoDB if URI is configured
  if (process.env.MONGODB_URI) {
    try {
      await connectToMongoDB();
      const dbUser = await User.findOne({ email: normalizedEmail });
      if (dbUser) {
        return {
          id: dbUser._id.toString(),
          name: dbUser.name,
          email: dbUser.email,
          password: dbUser.password,
          createdAt: dbUser.createdAt ? dbUser.createdAt.toISOString() : new Date().toISOString(),
        };
      }
    } catch (err) {
      console.warn("MongoDB connection unavailable, falling back to local persistent store:", err);
    }
  }

  // Fallback to local persistent store
  const localUsers = getLocalUsers();
  const match = localUsers.find((u) => u.email.toLowerCase().trim() === normalizedEmail);
  return match || null;
}

export async function createUser(name: string, email: string, plainPassword: string): Promise<UserAccount> {
  const normalizedEmail = email.toLowerCase().trim();
  const hashedPassword = await bcrypt.hash(plainPassword, 10);

  // Try MongoDB if URI is configured
  if (process.env.MONGODB_URI) {
    try {
      await connectToMongoDB();
      const dbUser = await User.create({
        name,
        email: normalizedEmail,
        password: hashedPassword,
      });
      return {
        id: dbUser._id.toString(),
        name: dbUser.name,
        email: dbUser.email,
        password: dbUser.password,
        createdAt: new Date().toISOString(),
      };
    } catch (err) {
      console.warn("MongoDB create failed, saving to local persistent store:", err);
    }
  }

  // Fallback to local persistent store
  const localUsers = getLocalUsers();
  const newUser: UserAccount = {
    id: `usr_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    name,
    email: normalizedEmail,
    password: hashedPassword,
    createdAt: new Date().toISOString(),
  };

  localUsers.push(newUser);
  saveLocalUsers(localUsers);
  return newUser;
}
