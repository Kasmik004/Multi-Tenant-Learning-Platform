"use client";

import { type FormEvent, useState } from "react";

import { useAuth } from "./AuthProvider";

/**
 * Login form. Platform accounts leave "Tenant slug" empty.
 * Tenant accounts fill it in (the slug identifies which tenant to authenticate against).
 */
export function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantSlug, setTenantSlug] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password, tenantSlug || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center px-4">
      <form onSubmit={handleSubmit} className="card w-full max-w-sm space-y-4">
        <div>
          <h1 className="text-xl font-semibold">Sign in</h1>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Platform admins: leave tenant slug empty.
          </p>
        </div>

        {error && <div className="alert-error">{error}</div>}

        <div>
          <label htmlFor="login-email" className="label">Email</label>
          <input
            id="login-email"
            type="email"
            className="input"
            placeholder="admin@example.com"
            required
            autoFocus
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="login-password" className="label">Password</label>
          <input
            id="login-password"
            type="password"
            className="input"
            placeholder="••••••••"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="login-tenant" className="label">
            Tenant slug <span style={{ color: "var(--muted)" }}>(optional)</span>
          </label>
          <input
            id="login-tenant"
            type="text"
            className="input"
            placeholder="acme"
            value={tenantSlug}
            onChange={(e) => setTenantSlug(e.target.value)}
          />
        </div>

        <button type="submit" className="btn btn-primary w-full" disabled={busy}>
          {busy ? <span className="spinner" /> : "Sign in"}
        </button>
      </form>
    </main>
  );
}
