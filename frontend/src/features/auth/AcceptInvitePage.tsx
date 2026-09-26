"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/features/auth/AuthProvider";

function AcceptInviteForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { acceptInvite, user } = useAuth();
  
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const qToken = searchParams.get("token");
    if (qToken) {
      setToken(qToken);
    }
  }, [searchParams]);

  // If already logged in, redirect them home.
  if (user) {
    router.push("/");
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await acceptInvite(token, password);
      router.push("/"); // Successfully accepted, go to dashboard
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to accept invite");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center px-4 py-12">
      <form onSubmit={handleSubmit} className="card w-full max-w-sm space-y-4">
        <div>
          <h1 className="text-xl font-semibold">Accept Invitation</h1>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Enter your invite token and set a password to activate your account.
          </p>
        </div>

        {error && <div className="alert-error">{error}</div>}

        <div>
          <label className="label">Invite Token</label>
          <input
            type="text"
            className="input font-mono text-sm"
            required
            autoFocus={!token}
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="paste token here"
          />
        </div>

        <div>
          <label className="label">New Password</label>
          <input
            type="password"
            className="input"
            required
            minLength={8}
            autoFocus={Boolean(token)}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
          <p className="text-xs mt-1 text-[var(--muted)]">Minimum 8 characters</p>
        </div>

        <button type="submit" className="btn btn-primary w-full" disabled={busy || !token || !password}>
          {busy ? <span className="spinner mx-auto" /> : "Set Password & Join"}
        </button>
      </form>
    </main>
  );
}

export function AcceptInvitePage() {
  return (
    <Suspense fallback={<main className="flex flex-1 items-center justify-center p-8"><span className="spinner spinner-lg" /></main>}>
      <AcceptInviteForm />
    </Suspense>
  );
}

