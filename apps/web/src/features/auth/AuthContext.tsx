import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import type { AuthUser } from "../../api/types";

interface AuthContextValue {
  ready: boolean;
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (login: string, password: string) => Promise<void>;
  logout: () => void;
}

const STORAGE_KEY = "podiumforge.auth";
const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        if (active) setReady(true);
        return;
      }

      try {
        const parsed = JSON.parse(raw) as { token: string; user: AuthUser };
        const verifiedUser = await api.me(parsed.token);
        if (!active) return;
        setToken(parsed.token);
        setUser(verifiedUser);
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ token: parsed.token, user: verifiedUser }));
      } catch {
        if (!active) return;
        setToken(null);
        setUser(null);
        localStorage.removeItem(STORAGE_KEY);
      } finally {
        if (active) setReady(true);
      }
    }

    void restoreSession();
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ready,
      token,
      user,
      isAuthenticated: Boolean(token && user),
        login: async (loginValue: string, password: string) => {
          const response = await api.login(loginValue, password);
          setToken(response.access_token);
          setUser(response.user);
        localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({ token: response.access_token, user: response.user }),
        );
      },
        logout: () => {
          setToken(null);
          setUser(null);
          localStorage.removeItem(STORAGE_KEY);
        },
    }),
    [ready, token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
