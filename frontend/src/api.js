// Thin API client. Uses the Vite proxy, so all calls go to /api/*.
const TOKEN_KEY = "tt_token";

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

  const res = await fetch(`/api${path}`, opts);
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

  // reference
  timeSlots: () => request("/reference/time-slots"),
  teachers: () => request("/reference/teachers"),

  // timetable
  activeTimetable: () => request("/timetable/active"),
  generate: () => request("/timetable/generate", { method: "POST" }),
  approve: (v) => request(`/timetable/approve/${v}`, { method: "POST" }),
  versions: () => request("/timetable/versions"),

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
