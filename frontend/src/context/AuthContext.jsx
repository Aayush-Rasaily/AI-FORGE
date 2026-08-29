import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiUrl } from "../config/api";

const TOKEN_KEY = "aiforge_access_token";
const REFRESH_KEY = "aiforge_refresh_token";
const USER_KEY = "aiforge_user";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [loading, setLoading] = useState(false);

  const persist = useCallback((access, refresh, profile) => {
    if (access) localStorage.setItem(TOKEN_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
    if (profile) localStorage.setItem(USER_KEY, JSON.stringify(profile));
    setToken(access);
    setUser(profile);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const login = useCallback(async (email, password) => {
    setLoading(true);
    try {
      const res = await fetch(apiUrl("auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Login failed");
      }
      persist(data.access_token, data.refresh_token, data.user);
      return data;
    } finally {
      setLoading(false);
    }
  }, [persist]);

  useEffect(() => {
    if (!token) return;
    fetch(apiUrl("auth/me"), {
      headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
    })
      .then((response) => {
        if (response.ok) return response.json();
        logout();
        return null;
      })
      .then((data) => {
        if (data?.user) {
          setUser(data.user);
          localStorage.setItem(USER_KEY, JSON.stringify(data.user));
        }
      })
      .catch((error) => {
        console.warn("Authentication validation unavailable:", error?.message || error);
      });
  }, [logout, token]);

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      isAuthenticated: Boolean(token && user),
      login,
      logout,
      getAuthHeaders: () => (token ? { Authorization: `Bearer ${token}` } : {}),
    }),
    [user, token, loading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}
