"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";

import { createApiClient, type Schemas } from "@/lib/api/client";

// ─── Types ──────────────────────────────────────────────────────────────────

type MeRead = Schemas["MeRead"];

interface AuthState {
  /** JWT access token. */
  token: string | null;
  /** Current user profile from /auth/me. null while loading or when logged out. */
  user: MeRead | null;
  /** True during the initial /auth/me fetch on page load. */
  loading: boolean;
}

interface AuthActions {
  /** Log in with email + password (and optional tenant slug for tenant accounts). */
  login: (email: string, password: string, tenantSlug?: string) => Promise<void>;
  /** Accept an invite token, set a password, and auto-login. */
  acceptInvite: (token: string, password: string) => Promise<void>;
  /** Clear token and user. */
  logout: () => void;
}

type AuthContextValue = AuthState & AuthActions;

const AuthContext = createContext<AuthContextValue | null>(null);

// ─── Local storage key ──────────────────────────────────────────────────────

const TOKEN_KEY = "mle_access_token";

function readToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

function writeToken(t: string) {
  localStorage.setItem(TOKEN_KEY, t);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// ─── Provider ───────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token: null,
    user: null,
    loading: true,
  });

  // Fetch /auth/me using a token. Returns the user or null.
  const fetchMe = useCallback(async (accessToken: string): Promise<MeRead | null> => {
    const api = createApiClient({ token: accessToken });
    const { data } = await api.GET("/api/v1/auth/me");
    return data ?? null;
  }, []);

  // On mount: try to restore session from localStorage.
  useEffect(() => {
    const saved = readToken();
    if (!saved) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState({ token: null, user: null, loading: false });
      return;
    }

    fetchMe(saved)
      .then((user) => {
        if (user) {
          setState({ token: saved, user, loading: false });
        } else {
          clearToken();
          setState({ token: null, user: null, loading: false });
        }
      })
      .catch(() => {
        clearToken();
        setState({ token: null, user: null, loading: false });
      });
  }, [fetchMe]);

  const login = useCallback(
    async (email: string, password: string, tenantSlug?: string) => {
      const api = createApiClient();
      const { data, error } = await api.POST("/api/v1/auth/login", {
        body: { email, password, tenant_slug: tenantSlug || null },
      });

      if (error || !data) {
        // Try to pull a readable message from the error body.
        const body = error as Record<string, unknown> | undefined;
        const nested = body?.error as { message?: string } | undefined;
        throw new Error(nested?.message ?? "Login failed");
      }

      const accessToken = data.access_token;
      writeToken(accessToken);

      const user = await fetchMe(accessToken);
      setState({ token: accessToken, user, loading: false });
    },
    [fetchMe],
  );

  const acceptInvite = useCallback(
    async (inviteToken: string, password: string) => {
      const api = createApiClient();
      const { data, error } = await api.POST("/api/v1/auth/accept-invite", {
        body: { token: inviteToken, password, confirm_password: password },
      });

      if (error || !data) {
        const body = error as Record<string, unknown> | undefined;
        const nested = body?.error as { message?: string } | undefined;
        throw new Error(nested?.message ?? "Failed to accept invite");
      }

      const accessToken = data.access_token;
      writeToken(accessToken);

      const user = await fetchMe(accessToken);
      setState({ token: accessToken, user, loading: false });
    },
    [fetchMe],
  );

  const logout = useCallback(() => {
    clearToken();
    setState({ token: null, user: null, loading: false });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, login, acceptInvite, logout }),
    [state, login, acceptInvite, logout],
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}

// ─── Hook ───────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
