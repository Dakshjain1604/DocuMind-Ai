"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, CheckCircle2, ArrowRight } from "lucide-react";
import { AuthShell, AuthField } from "../components/AuthShell";
import { Button } from "@/components/ui/button";

export default function SigninPage() {
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
      const res = await fetch("/api/auth/signin", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        let msg = "Sign in failed";
        try {
          const body = await res.json();
          if (body?.message) msg = body.message;
        } catch {
          /* non-JSON error body; keep the generic message */
        }
        setError(msg);
        setBusy(false);
        return;
      }
      setSuccess("Session opened · Redirecting to studio…");
      setTimeout(() => router.push("/Dashboard"), 900);
    } catch {
      setError("Could not reach the server. Is it running?");
      setBusy(false);
    }
  };

  return (
    <AuthShell
      kicker="Ingress"
      heading="Resume your session."
      sub="Sign in to your DocuMind studio workspace."
      footer={
        <>
          New to DocuMind?{" "}
          <Link
            href="/signup"
            className="text-white font-semibold hover:underline inline-flex items-center gap-1 ml-1"
          >
            <span>Request access</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
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
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
          required
        />

        <Button
          type="submit"
          disabled={busy}
          size="lg"
          className="mt-3 w-full justify-between gap-2 bg-white text-zinc-950 hover:bg-zinc-200"
        >
          <span>{busy ? "Opening session…" : "Open Session"}</span>
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
