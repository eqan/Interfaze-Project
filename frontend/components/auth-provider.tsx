"use client";

import {
  createContext,
  startTransition,
  useContext,
  useEffect,
  useState,
} from "react";

import {
  fetchAuthSession,
  loginWithGoogleCredential,
  logoutAuthSession,
} from "@/lib/api/auth";
import type { AuthenticatedUser, AuthStatus } from "@/types/auth";

type AuthContextValue = {
  status: AuthStatus;
  user: AuthenticatedUser | null;
  error: string | null;
  signInWithGoogleCredential: (credential: string) => Promise<void>;
  signOut: () => Promise<void>;
  clearError: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function getErrorMessage(error: unknown) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Authentication failed. Please try again.";
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;

    async function bootstrapSession() {
      try {
        const verifiedUser = await fetchAuthSession();

        if (isCancelled) {
          return;
        }

        setUser(verifiedUser);
        setError(null);
        setStatus("authenticated");
      } catch {
        if (isCancelled) {
          return;
        }

        setUser(null);
        setStatus("unauthenticated");
      }
    }

    bootstrapSession();

    return () => {
      isCancelled = true;
    };
  }, []);

  async function signInWithGoogleCredential(credential: string) {
    setError(null);
    setStatus("loading");

    try {
      const verifiedUser = await loginWithGoogleCredential(credential);

      startTransition(() => {
        setUser(verifiedUser);
        setStatus("authenticated");
      });
    } catch (signInError) {
      setUser(null);
      setStatus("unauthenticated");
      setError(getErrorMessage(signInError));
      throw signInError;
    }
  }

  async function signOut() {
    try {
      await logoutAuthSession();
    } catch {
      // Clear local session state even if the logout request fails.
    }

    startTransition(() => {
      setUser(null);
      setError(null);
      setStatus("unauthenticated");
    });
  }

  const value = {
    status,
    user,
    error,
    signInWithGoogleCredential,
    signOut,
    clearError: () => setError(null),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }

  return context;
}
