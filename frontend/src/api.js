// Mock API – returns static data, no backend required.
import {
  MOCK_BRANDING,
  MOCK_TIME_SLOTS,
  MOCK_TEACHERS,
  MOCK_CLASSES,
  MOCK_TIMETABLE_ENTRIES,
  MOCK_SUBSTITUTIONS,
  MOCK_LEAVES,
  MOCK_NOTIFICATIONS,
  MOCK_OVERVIEW,
  MOCK_ACTIVITY,
  MOCK_FAIRNESS,
  MOCK_CANDIDATES,
  MOCK_SUGGESTIONS,
  MOCK_USER,
} from "./mockData.js";

// Keep these exports so existing imports don't break.
export const API_BASE = "";
export function apiUrl(path) { return path; }
export function getToken() { return "mock-token"; }
export function setToken() {}

// Small delay to simulate network feel.
const delay = (ms = 120) => new Promise((r) => setTimeout(r, ms));

// Local mutable state so UI interactions actually work during the session.
let notifications = [...MOCK_NOTIFICATIONS];
let leaves = [...MOCK_LEAVES];
let teachers = [...MOCK_TEACHERS];
let nextLeaveId = 99;
let nextTeacherId = 10;

export const api = {
  // auth
  login: async () => { await delay(); return { access_token: "mock-token" }; },
  me: async () => { await delay(); return MOCK_USER; },
  changePassword: async () => { await delay(); return { ok: true }; },

  // accounts (Teachers page)
  listAccounts: async () => { await delay(); return teachers; },
  createAccount: async (payload) => {
    await delay();
    const t = { id: nextTeacherId++, ...payload, role: "TEACHER", is_active: true, temp_password: "TempPass@123" };
    teachers = [...teachers, t];
    return t;
  },
  updateAccount: async (id, payload) => {
    await delay();
    teachers = teachers.map((t) => (t.id === id ? { ...t, ...payload } : t));
    return teachers.find((t) => t.id === id);
  },
  resetPassword: async (id) => { await delay(200); return { temp_password: "Reset@" + id + "123" }; },

  // reference
  timeSlots: async () => { await delay(); return MOCK_TIME_SLOTS; },
  teachers: async () => { await delay(); return MOCK_TEACHERS; },

  // timetable
  activeTimetable: async () => { await delay(); return MOCK_TIMETABLE_ENTRIES; },
  generate: async () => { await delay(800); return { success: true, version: 3, entries: MOCK_TIMETABLE_ENTRIES.length, message: "" }; },
  approve: async () => { await delay(); return { ok: true }; },
  versions: async () => { await delay(); return [{ version: 1 }, { version: 2 }]; },
  viewOptions: async () => {
    await delay();
    return {
      teachers: MOCK_TEACHERS.map((t) => ({ id: t.id, name: t.name, role: t.role })),
      classes: MOCK_CLASSES,
    };
  },
  teacherTimetable: async (id) => {
    await delay();
    return MOCK_TIMETABLE_ENTRIES.filter((e) => e.teacher_id === id);
  },
  classTimetable: async (id) => {
    await delay();
    return MOCK_TIMETABLE_ENTRIES.filter((e) => e.class_id === id);
  },

  // leaves
  myLeaves: async () => { await delay(); return leaves; },
  createLeave: async (payload) => {
    await delay(400);
    const lv = { id: nextLeaveId++, ...payload, status: "ACTIVE" };
    leaves = [lv, ...leaves];
    return lv;
  },
  cancelLeave: async (id) => {
    await delay();
    leaves = leaves.map((l) => (l.id === id ? { ...l, status: "CANCELLED" } : l));
    return { ok: true };
  },

  // substitutions
  substitutions: async () => { await delay(); return MOCK_SUBSTITUTIONS; },
  candidates: async () => { await delay(300); return MOCK_CANDIDATES; },
  suggestions: async () => { await delay(300); return MOCK_SUGGESTIONS; },
  assignSub: async (subId, teacherId) => {
    await delay(400);
    const teacher = MOCK_TEACHERS.find((t) => t.id === teacherId);
    MOCK_SUBSTITUTIONS.forEach((s) => {
      if (s.id === subId) {
        s.status = "ASSIGNED";
        s.substitute_teacher = teacher?.name ?? "Unknown";
      }
    });
    return { ok: true };
  },

  // dashboard
  summary: async () => { await delay(); return MOCK_OVERVIEW; },
  overview: async () => { await delay(); return MOCK_OVERVIEW; },
  activity: async () => { await delay(); return MOCK_ACTIVITY; },
  fairness: async () => { await delay(); return MOCK_FAIRNESS; },
  leaveHistory: async () => { await delay(); return leaves; },

  // branding
  branding: async () => { await delay(); return MOCK_BRANDING; },

  // notifications
  notifications: async () => { await delay(); return notifications; },
  unreadCount: async () => { await delay(); return { unread: notifications.filter((n) => !n.is_read).length }; },
  markRead: async (id) => {
    await delay();
    notifications = notifications.map((n) => (n.id === id ? { ...n, is_read: true } : n));
    return { ok: true };
  },
  markAllRead: async () => {
    await delay();
    notifications = notifications.map((n) => ({ ...n, is_read: true }));
    return { ok: true };
  },
};
