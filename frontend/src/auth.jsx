import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";

const AuthCtx = createContext(null);

const DEFAULT_BRANDING = {
  institution_name: "JGI JAIN",
  institution_subtitle: "Deemed-to-be University",
  department_name: "Department of Computer Applications",
  product_name: "Timetable Management System",
  semester_label: "Even semester | 2026",
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [branding, setBranding] = useState(DEFAULT_BRANDING);

  useEffect(() => {
    async function boot() {
      try {
        const b = await api.branding();
        setBranding({ ...DEFAULT_BRANDING, ...b });
      } catch {
        /* keep defaults */
      }
      if (getToken()) {
        try {
          const me = await api.me();
          setUser(me);
        } catch {
          setToken(null);
        }
      }

      // No login screen: sign in automatically as the default account.
      // The backend still issues a token, so every API call stays authenticated.
      const DEFAULT_EMAIL = import.meta.env.VITE_DEFAULT_EMAIL || "anjana@college.edu";
      const DEFAULT_PASSWORD = import.meta.env.VITE_DEFAULT_PASSWORD || "password123";
      if (!getToken()) {
        try {
          const tok = await api.login(DEFAULT_EMAIL, DEFAULT_PASSWORD);
          setToken(tok.access_token);
          setUser(await api.me());
        } catch {
          /* user stays null; App shows a "can't reach the server" screen */
        }
      }

      setLoading(false);
    }
    boot();
  }, []);

  async function login(email, password) {
    const tok = await api.login(email, password);
    setToken(tok.access_token);
    const me = await api.me();
    setUser(me);
    return me;
  }

  async function refreshUser() {
    try {
      const me = await api.me();
      setUser(me);
      return me;
    } catch {
      return null;
    }
  }

  function logout() {
    setToken(null);
    setUser(null);
  }

  return (
    <AuthCtx.Provider value={{ user, loading, login, logout, branding, refreshUser }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  return useContext(AuthCtx);
}
