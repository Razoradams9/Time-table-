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

  let res;
  try {
    res = await fetch(apiUrl(path), { method, headers, body: payload });
  } catch {
    throw new Error("Cannot reach the server. Check your connection and try again.");
  }

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
    // An expired/invalid token on an authenticated call: drop it and tell the app.
    if (res.status === 401 && auth && getToken()) {
      setToken(null);
      window.dispatchEvent(new Event("tt:unauthorized"));
    }
    throw new Error(detail);
  }

  if (res.status === 204) return null;
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

export const api = {
  // ----- auth -----
  login: async (email, password) => {
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
  workload: (start, end, teacherId) => {
    const q = new URLSearchParams();
    if (start) q.set("start", start);
    if (end) q.set("end", end);
    if (teacherId != null) q.set("teacher_id", teacherId);
    const qs = q.toString();
    return request(`/api/dashboard/workload${qs ? `?${qs}` : ""}`);
  },
  courses: (teacherId) =>
    request(`/api/courses${teacherId != null ? `?teacher_id=${teacherId}` : ""}`),
  // ----- compensations (make-up classes) -----
  compensations: (params = {}) => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") q.set(k, v);
    }
    const qs = q.toString();
    return request(`/api/compensations${qs ? `?${qs}` : ""}`);
  },
  compensationSummary: (teacherId) =>
    request(`/api/compensations/summary${teacherId != null ? `?teacher_id=${teacherId}` : ""}`),
  compensationCalendar: (on) => request(`/api/compensations/calendar?on=${on}`),
  compensationSuggestions: (id) => request(`/api/compensations/${id}/suggestions`),
  confirmCompensation: (id, slot) =>
    request(`/api/compensations/${id}/confirm`, { method: "POST", body: slot }),
  rescheduleCompensation: (id, slot) =>
    request(`/api/compensations/${id}/reschedule`, { method: "POST", body: slot }),
  completeCompensation: (id) => request(`/api/compensations/${id}/complete`, { method: "POST" }),
  cancelCompensation: (id) => request(`/api/compensations/${id}/cancel`, { method: "POST" }),
  repropose: (id) => request(`/api/compensations/${id}/repropose`, { method: "POST" }),
  backfillCompensations: () => request("/api/compensations/backfill", { method: "POST" }),
  leaveHistory: (teacherId) => request(`/api/dashboard/leave-history/${teacherId}`),

  // ----- branding -----
  branding: () => request("/api/branding", { auth: false }),

  // ----- notifications -----
  notifications: () => request("/api/notifications"),
  unreadCount: () => request("/api/notifications/unread-count"),
  markRead: (id) => request(`/api/notifications/${id}/read`, { method: "POST" }),
  markAllRead: () => request("/api/notifications/read-all", { method: "POST" }),
};
