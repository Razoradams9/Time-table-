import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";

export const AuthCtx = createContext(null);

const DEFAULT_BRANDING = {
  institution_name: "JGI JAIN",
  institution_subtitle: "Deemed-to-be University",
  department_name: "Department of Computer Science and IT",
  product_name: "Timetable Management System",
  semester_label: "Even semester | 2026",
};

// The backend /me endpoint returns a Teacher with `id`; the UI expects
// `teacher_id`. Normalize so both are always present.
function normalizeUser(me) {
  if (!me) return me;
  return { ...me, teacher_id: me.teacher_id ?? me.id };
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [branding, setBranding] = useState(DEFAULT_BRANDING);
  const [sessionMessage, setSessionMessage] = useState("");

  useEffect(() => {
    async function boot() {
      try {
        const b = await api.branding();
        setBranding({ ...DEFAULT_BRANDING, ...b });
      } catch {
        /* keep defaults */
      }
      // Restore a saved session only; otherwise the Login page is shown.
      if (getToken()) {
        try {
          setUser(normalizeUser(await api.me()));
        } catch {
          setToken(null);
        }
      }
      setLoading(false);
    }
    boot();
  }, []);

  // api.js fires this when an authenticated call comes back 401.
  useEffect(() => {
    function onUnauthorized() {
      setUser(null);
      setSessionMessage("Your session has expired. Please sign in again.");
    }
    window.addEventListener("tt:unauthorized", onUnauthorized);
    return () => window.removeEventListener("tt:unauthorized", onUnauthorized);
  }, []);

  async function login(email, password) {
    setSessionMessage("");
    await api.login(email, password);
    const me = normalizeUser(await api.me());
    setUser(me);
    return me;
  }

  async function refreshUser() {
    try {
      const me = normalizeUser(await api.me());
      setUser(me);
      return me;
    } catch {
      return null;
    }
  }

  function logout() {
    setToken(null);
    setUser(null);
    setSessionMessage("");
  }

  const clearSessionMessage = useCallback(() => setSessionMessage(""), []);

  return (
    <AuthCtx.Provider
      value={{ user, loading, login, logout, branding, refreshUser, sessionMessage, clearSessionMessage }}
    >
      {children}
    </AuthCtx.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthCtx);
}
