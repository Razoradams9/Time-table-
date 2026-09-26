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

  function logout() {
    setToken(null);
    setUser(null);
  }

  return (
    <AuthCtx.Provider value={{ user, loading, login, logout, branding }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  return useContext(AuthCtx);
}
