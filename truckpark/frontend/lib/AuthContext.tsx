"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, apiErrorMessage } from "./api";
import { AuthUser, clearTokens, getStoredUser, homeRouteForRole, setTokens } from "./auth";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (mobile: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    setUser(getStoredUser());
    setLoading(false);
  }, []);

  async function login(mobile: string, password: string) {
    try {
      const { data } = await api.post("/auth/login", { mobile, password });
      setTokens(data.access_token, data.refresh_token, data.user);
      setUser(data.user);
      router.replace(homeRouteForRole(data.user.role));
    } catch (err) {
      throw new Error(apiErrorMessage(err, "Login failed. Check your mobile number and password."));
    }
  }

  function logout() {
    clearTokens();
    setUser(null);
    router.replace("/login");
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
