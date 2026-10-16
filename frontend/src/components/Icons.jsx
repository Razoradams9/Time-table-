// Shared inline line-icons (1.8px stroke, mono-tone). Used by the sidebar,
// header and dashboard so every icon in the app comes from one place.
export const Icon = ({ path, filled, size }) => (
  <svg
    className="ic"
    viewBox="0 0 24 24"
    width={size}
    height={size}
    fill={filled ? "currentColor" : "none"}
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    {path}
  </svg>
);

export const icons = {
  dashboard: <><rect x="3" y="3" width="7" height="9" rx="1" /><rect x="14" y="3" width="7" height="5" rx="1" /><rect x="14" y="12" width="7" height="9" rx="1" /><rect x="3" y="16" width="7" height="5" rx="1" /></>,
  timetable: <><rect x="3" y="4" width="18" height="17" rx="2" /><path d="M3 9h18M8 2v4M16 2v4" /></>,
  teachers: <><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6M16 4.5a3.5 3.5 0 010 7M18 14.3c2.3.7 3.5 2.7 3.5 5.7" /></>,
  classes: <><path d="M3 21h18M5 21V9l7-5 7 5v12M9 21v-6h6v6" /></>,
  subjects: <><path d="M3 5a2 2 0 012-2h6v18H5a2 2 0 01-2-2zM21 5a2 2 0 00-2-2h-6v18h6a2 2 0 002-2z" /></>,
  substitutions: <><path d="M4 8h15l-4-4M20 16H5l4 4" /></>,
  attendance: <><rect x="3" y="3" width="18" height="18" rx="3" /><path d="M8 12l3 3 5-6" /></>,
  leaves: <><path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z" /><path d="M14 3v5h5M9 13h6M9 17h6" /></>,
  messages: <><path d="M21 12a8 8 0 01-11.6 7.1L3 21l1.9-5.4A8 8 0 1121 12z" /></>,
  reports: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>,
  lock: <><rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V7a4 4 0 018 0v4" /></>,
  help: <><circle cx="12" cy="12" r="9" /><path d="M9.5 9.5a2.5 2.5 0 114 2c-.9.6-1.5 1-1.5 2M12 17h.01" /></>,
  bell: <><path d="M6 8a6 6 0 0112 0c0 7 3 8 3 8H3s3-1 3-8M10 20a2 2 0 004 0" /></>,
  logout: <><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" /></>,
  checkCircle: <><circle cx="12" cy="12" r="9" /><path d="M8 12.5l3 3 5-6" /></>,
  minusCircle: <><circle cx="12" cy="12" r="9" /><path d="M8 12h8" /></>,
  calendarPlus: <><rect x="3" y="4" width="18" height="17" rx="2" /><path d="M3 9h18M8 2v4M16 2v4M12 12v6M9 15h6" /></>,
  userPlus: <><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6M19 8v6M16 11h6" /></>,
};
