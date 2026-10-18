// Real API client – talks to the FastAPI backend.
//
// In dev, requests go to "/api/..." which the Vite proxy (vite.config.js)
// forwards to http://127.0.0.1:8010. In production set VITE_API_URL to the
// backend's base URL (no trailing slash).

export const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export function apiUrl(path) {
  return `${API_BASE}${path}`;
}

// --- token storage -------------------------------------------------------
const TOKEN_KEY = "tt_token";

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore storage errors */
  }
}

// --- low-level request helper -------------------------------------------
async function request(path, { method = "GET", body, form, auth = true } = {}) {
  const headers = {};
  if (auth) {
    const t = getToken();
    if (t) headers["Authorization"] = `Bearer ${t}`;
  }

  let payload;
  if (form) {
    // application/x-www-form-urlencoded (used by the OAuth2 login endpoint)
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload = new URLSearchParams(form).toString();
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(apiUrl(path), { method, headers, body: payload });

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      if (data && data.detail) {
        detail = Array.isArray(data.detail)
          ? data.detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
          : data.detail;
      }
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }

  if (res.status === 204) return null;
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

const defaultEmail = import.meta.env.VITE_DEFAULT_EMAIL || "anjana@college.edu";
const defaultPassword = import.meta.env.VITE_DEFAULT_PASSWORD || "password123";

export const api = {
  // ----- auth -----
  login: async (email = defaultEmail, password = defaultPassword) => {
    // Backend expects OAuth2 form fields: username (=email) + password.
    const tok = await request("/api/auth/login", {
      method: "POST",
      form: { username: email, password },
      auth: false,
    });
    if (tok?.access_token) setToken(tok.access_token);
    return tok;
  },
  me: () => request("/api/auth/me"),
  changePassword: (current_password, new_password) =>
    request("/api/auth/change-password", {
      method: "POST",
      body: { current_password, new_password },
    }),

  // ----- accounts (Teachers page) -----
  listAccounts: () => request("/api/accounts"),
  createAccount: (payload) => request("/api/accounts", { method: "POST", body: payload }),
  updateAccount: (id, payload) => request(`/api/accounts/${id}`, { method: "PATCH", body: payload }),
  resetPassword: (id) => request(`/api/accounts/${id}/reset-password`, { method: "POST" }),

  // ----- reference -----
  timeSlots: () => request("/api/reference/time-slots"),
  teachers: () => request("/api/reference/teachers"),

  // ----- timetable -----
  activeTimetable: () => request("/api/timetable/active"),
  generate: () => request("/api/timetable/generate", { method: "POST" }),
  approve: (version) => request(`/api/timetable/approve/${version}`, { method: "POST" }),
  versions: () => request("/api/timetable/versions"),
  viewOptions: () => request("/api/timetable/view/options"),
  teacherTimetable: (id) => request(`/api/timetable/view/teacher/${id}`),
  classTimetable: (id) => request(`/api/timetable/view/class/${id}`),

  // ----- leaves -----
  myLeaves: () => request("/api/leaves"),
  createLeave: (payload) => request("/api/leaves", { method: "POST", body: payload }),
  cancelLeave: (id) => request(`/api/leaves/${id}`, { method: "DELETE" }),

  // ----- substitutions -----
  substitutions: (on) => request(`/api/substitutions${on ? `?on=${on}` : ""}`),
  candidates: (subId) => request(`/api/substitutions/${subId}/candidates`),
  suggestions: (subId) => request(`/api/substitutions/${subId}/suggestions`),
  assignSub: (subId, teacherId) =>
    request(`/api/substitutions/${subId}/assign`, {
      method: "POST",
      body: { substitute_teacher_id: teacherId },
    }),

  // ----- dashboard -----
  summary: (on) => request(`/api/dashboard/summary${on ? `?on=${on}` : ""}`),
  overview: (on) => request(`/api/dashboard/overview${on ? `?on=${on}` : ""}`),
  activity: (limit = 10) => request(`/api/dashboard/activity?limit=${limit}`),
  fairness: (start, end) => request(`/api/dashboard/fairness?start=${start}&end=${end}`),
  leaveHistory: (teacherId) => request(`/api/dashboard/leave-history/${teacherId}`),

  // ----- branding -----
  branding: () => request("/api/branding", { auth: false }),

  // ----- notifications -----
  notifications: () => request("/api/notifications"),
  unreadCount: () => request("/api/notifications/unread-count"),
  markRead: (id) => request(`/api/notifications/${id}/read`, { method: "POST" }),
  markAllRead: () => request("/api/notifications/read-all", { method: "POST" }),
};
