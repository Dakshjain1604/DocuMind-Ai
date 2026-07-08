"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import axios from "axios";
import { AuthShell, AuthField } from "../components/AuthShell";

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
      setSuccess("workspace provisioned · redirecting to sign in…");
      setTimeout(() => router.push("/signin"), 1100);
    } catch (err: unknown) {
      let msg = "sign up failed";
      if (axios.isAxiosError(err)) msg = err.response?.data?.message || msg;
      else if (err instanceof Error) msg = err.message;
      setError(msg);
      setBusy(false);
    }
  };

  return (
    <AuthShell
      kicker="entry · enrollment"
      heading="Open a new workspace."
      sub="Provision your DocuMind cartographer's desk."
      footer={
        <>
          Already enrolled?{" "}
          <Link
            href="/signin"
            className="border-b border-[var(--vermillion)] pb-0.5 text-[var(--paper)] hover:text-[var(--vermillion)]"
          >
            return to sign in →
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <AuthField
          label="name"
          type="text"
          autoComplete="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Your name"
          required
        />
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
          autoComplete="new-password"
          minLength={6}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="at least six characters"
          required
        />

        <button
          type="submit"
          disabled={busy}
          className="instrument mt-3 inline-flex items-center justify-between bg-[var(--vermillion)] px-5 py-3.5 font-mono-cap text-[12px] text-[var(--ink)] hover:bg-[var(--vermillion-hot)] disabled:cursor-not-allowed disabled:opacity-60"
        >
          <span>{busy ? "provisioning…" : "create workspace"}</span>
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
