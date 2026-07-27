"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import axios from "axios";
import { AlertCircle, CheckCircle2, ArrowRight } from "lucide-react";
import { AuthShell, AuthField } from "../components/AuthShell";
import { Button } from "@/components/ui/button";

export default function SignupPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setBusy(true);
    try {
      await axios.post("/api/auth/signup", { name, email, password });
      setSuccess("Workspace provisioned · Redirecting to sign in…");
      setTimeout(() => router.push("/signin"), 1100);
    } catch (err: unknown) {
      let msg = "Sign up failed";
      if (axios.isAxiosError(err)) msg = err.response?.data?.message || msg;
      else if (err instanceof Error) msg = err.message;
      setError(msg);
      setBusy(false);
    }
  };

  return (
    <AuthShell
      kicker="Enrollment"
      heading="Open a new workspace."
      sub="Provision your DocuMind studio environment."
      footer={
        <>
          Already enrolled?{" "}
          <Link
            href="/signin"
            className="text-indigo-400 font-semibold hover:underline inline-flex items-center gap-1 ml-1"
          >
            <span>Return to sign in</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <AuthField
          label="Full Name"
          type="text"
          autoComplete="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Your name"
          required
        />
        <AuthField
          label="Email Address"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@domain.com"
          required
        />
        <AuthField
          label="Password"
          type="password"
          autoComplete="new-password"
          minLength={6}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="At least six characters"
          required
        />

        <Button
          type="submit"
          disabled={busy}
          size="lg"
          className="mt-3 w-full gap-2 justify-between"
        >
          <span>{busy ? "Provisioning…" : "Create Workspace"}</span>
          <ArrowRight className="h-4 w-4" />
        </Button>

        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3.5 font-mono text-xs text-red-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        {success && (
          <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 font-mono text-xs text-emerald-400">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{success}</span>
          </div>
        )}
      </form>
    </AuthShell>
  );
}
