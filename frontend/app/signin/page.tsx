"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import axios from "axios";
import { AuthShell, AuthField } from "../components/AuthShell";

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
      await axios.post("/api/auth/signin", { email, password });
      setSuccess("session opened · redirecting…");
      setTimeout(() => router.push("/Dashboard"), 900);
    } catch (err: unknown) {
      let msg = "sign in failed";
      if (axios.isAxiosError(err)) msg = err.response?.data?.message || msg;
      else if (err instanceof Error) msg = err.message;
      setError(msg);
      setBusy(false);
    }
  };

  return (
    <AuthShell
      kicker="entry · ingress"
      heading="Resume the session."
      sub="Sign in to your DocuMind workspace."
      footer={
        <>
          New to DocuMind?{" "}
          <Link
            href="/signup"
            className="border-b border-[var(--vermillion)] pb-0.5 text-[var(--paper)] hover:text-[var(--vermillion)]"
          >
            request access →
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <AuthField
          label="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@domain.tld"
          required
        />
        <AuthField
          label="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
          required
        />

        <button
          type="submit"
          disabled={busy}
          className="instrument mt-3 inline-flex items-center justify-between bg-[var(--vermillion)] px-5 py-3.5 font-mono-cap text-[12px] text-[var(--ink)] hover:bg-[var(--vermillion-hot)] disabled:cursor-not-allowed disabled:opacity-60"
        >
          <span>{busy ? "dispatching…" : "open session"}</span>
          <span className="font-sans text-[15px] leading-none">→</span>
        </button>

        {error && (
          <p
            role="alert"
            className="border-l-2 border-[var(--vermillion)] bg-[var(--vermillion)]/10 px-4 py-3 font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--vermillion-hot)]"
          >
            ✕ {error}
          </p>
        )}
        {success && (
          <p className="border-l-2 border-[#7fa9a5] bg-[#1a4d4a]/20 px-4 py-3 font-mono text-[11px] uppercase tracking-[0.12em] text-[#7fa9a5]">
            ● {success}
          </p>
        )}
      </form>
    </AuthShell>
  );
}
