import { createContext, useContext, useEffect, useState } from "react";
import { api, setToken } from "./api";

export const AuthCtx = createContext(null);

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
      // Mock mode: always auto-login, no backend needed.
      try {
        const tok = await api.login();
        setToken(tok.access_token);
        setUser(await api.me());
      } catch {
        /* user stays null */
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

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthCtx);
}
