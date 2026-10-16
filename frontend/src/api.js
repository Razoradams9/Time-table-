// Thin API client. Uses the Vite proxy, so all calls go to /api/*.
const TOKEN_KEY = "tt_token";

// In production (Vercel) set VITE_API_URL to the Fly backend, e.g.
// https://timetable-backend.fly.dev  — then API calls go there directly.
// Locally it's empty, so calls hit "/api" and Vite proxies to the backend.
export const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export function apiUrl(path) {
  return `${API_BASE}/api${path}`;
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request(path, { method = "GET", body, form, headers = {} } = {}) {
  const opts = { method, headers: { ...headers } };
  const token = getToken();
  if (token) opts.headers["Authorization"] = `Bearer ${token}`;

  if (form) {
    opts.body = new URLSearchParams(form).toString();
    opts.headers["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (body !== undefined) {
    opts.body = JSON.stringify(body);
    opts.headers["Content-Type"] = "application/json";
  }

  const res = await fetch(apiUrl(path), opts);
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res;
}

export const api = {
  login: (email, password) =>
    request("/auth/login", { method: "POST", form: { username: email, password } }),
  me: () => request("/auth/me"),
  changePassword: (current_password, new_password) =>
    request("/auth/change-password", { method: "POST", body: { current_password, new_password } }),

  // account management (HOD)
  listAccounts: () => request("/accounts"),
  createAccount: (payload) => request("/accounts", { method: "POST", body: payload }),
  updateAccount: (id, payload) => request(`/accounts/${id}`, { method: "PATCH", body: payload }),
  resetPassword: (id) => request(`/accounts/${id}/reset-password`, { method: "POST" }),

  // reference
  timeSlots: () => request("/reference/time-slots"),
  teachers: () => request("/reference/teachers"),

  // timetable
  activeTimetable: () => request("/timetable/active"),
  generate: () => request("/timetable/generate", { method: "POST" }),
  approve: (v) => request(`/timetable/approve/${v}`, { method: "POST" }),
  versions: () => request("/timetable/versions"),
  viewOptions: () => request("/timetable/view/options"),
  teacherTimetable: (id) => request(`/timetable/view/teacher/${id}`),
  classTimetable: (id) => request(`/timetable/view/class/${id}`),

  // leaves
  myLeaves: () => request("/leaves"),
  createLeave: (payload) => request("/leaves", { method: "POST", body: payload }),
  cancelLeave: (id) => request(`/leaves/${id}`, { method: "DELETE" }),

  // substitutions
  substitutions: (on) => request(`/substitutions${on ? `?on=${on}` : ""}`),
  candidates: (id) => request(`/substitutions/${id}/candidates`),
  suggestions: (id) => request(`/substitutions/${id}/suggestions`),
  assignSub: (id, teacherId) =>
    request(`/substitutions/${id}/assign`, {
      method: "POST",
      body: { substitute_teacher_id: teacherId },
    }),

  // dashboard
  summary: (on) => request(`/dashboard/summary${on ? `?on=${on}` : ""}`),
  overview: (on) => request(`/dashboard/overview${on ? `?on=${on}` : ""}`),
  activity: (limit = 10) => request(`/dashboard/activity?limit=${limit}`),
  fairness: (start, end) => request(`/dashboard/fairness?start=${start}&end=${end}`),
  leaveHistory: (teacherId) => request(`/dashboard/leave-history/${teacherId}`),

  // public
  branding: () => request("/branding"),

  // notifications
  notifications: () => request("/notifications"),
  unreadCount: () => request("/notifications/unread-count"),
  markRead: (id) => request(`/notifications/${id}/read`, { method: "POST" }),
  markAllRead: () => request("/notifications/read-all", { method: "POST" }),
};
