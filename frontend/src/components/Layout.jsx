import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth.jsx";

const Ic = ({ d, size = 17 }) => (
  <svg className="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
    width={size} height={size}>
    {d}
  </svg>
);

const ICONS = {
  dashboard:      <><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></>,
  timetable:      <><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M3 10h18M8 2v4M16 2v4"/></>,
  teachers:       <><circle cx="9" cy="7" r="3"/><path d="M2 21v-2a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v2"/><path d="M17 11l2 2 4-4"/></>,
  classes:        <><path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6"/></>,
  subjects:       <><path d="M4 4h11a2 2 0 0 1 2 2v14H6a2 2 0 0 1-2-2z"/><path d="M17 6h3v14H8"/></>,
  substitutions:  <><path d="M4 7h13l-3-3M20 17H7l3 3"/></>,
  attendance:     <><rect x="3" y="4" width="18" height="18" rx="2"/><path d="m9 14 2 2 4-4"/></>,
  messages:       <><path d="M4 4h16v12H7l-3 3z"/></>,
  reports:        <><path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/></>,
  settings:       <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></>,
  help:           <><circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 0 1 4.5 1.5c0 1.5-2 2-2 3.5M12 17h.01"/></>,
  bell:           <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></>,
  inbox:          <><path d="M4 4h16v12H7l-3 3z"/></>,
  star:           <><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></>,
  important:      <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></>,
  draft:          <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></>,
  send:           <><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></>,
  trash:          <><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6M10 11v6M14 11v6M9 6V4h6v2"/></>,
  chevronDown:    <><polyline points="6 9 12 15 18 9"/></>,
};

const mainNav = [
  { to: "/",             icon: "dashboard",     label: "Dashboard",     end: true },
  { to: "/timetable",    icon: "timetable",     label: "Timetable" },
  { to: "/teachers",     icon: "teachers",      label: "Teachers",      hod: true },
  { to: "/classes",      icon: "classes",       label: "Classes",       hod: true },
  { to: "/subjects",     icon: "subjects",      label: "Subjects",      hod: true, soon: true },
  { to: "/substitutions",icon: "substitutions", label: "Substitutions", hod: true },
  { to: "/attendance",   icon: "attendance",    label: "Attendance",    soon: true },
  { to: "/leaves",       icon: "attendance",    label: "Leaves" },
  { to: "/notifications",icon: "messages",      label: "Messages" },
  { to: "/fairness",     icon: "reports",       label: "Reports",       hod: true },
];
const bottomNav = [
  { to: "/settings", icon: "settings", label: "Settings", soon: true },
  { to: "/help",     icon: "help",     label: "Help",     soon: true },
];

export default function Layout() {
  const { user, logout, branding } = useAuth();
  const [unread, setUnread] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);
  const isHod = user.role === "HOD";
  const location = useLocation();

  useEffect(() => {
    let alive = true;
    async function poll() {
      try { const r = await api.unreadCount(); if (alive) setUnread(r.unread); } catch {}
    }
    poll();
    const t = setInterval(poll, 15000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  useEffect(() => { setMobileOpen(false); }, [location.pathname]);

  const initials = user.name.replace(/\(.*?\)/g, "").trim()
    .split(/\s+/).slice(0, 2).map(w => w[0]).join("").toUpperCase();

  const linkCls = ({ isActive }) => "side-link" + (isActive ? " active" : "");

  const renderNavItem = (item) => {
    if (item.hod && !isHod) return null;
    if (item.soon) return (
      <span key={item.label} className="side-link soon">
        <Ic d={ICONS[item.icon]} />
        <span>{item.label}</span>
        <span className="soon-dot">soon</span>
      </span>
    );
    return (
      <NavLink key={item.label} to={item.to} end={item.end} className={linkCls}>
        <Ic d={ICONS[item.icon]} />
        <span>{item.label}</span>
        {item.label === "Messages" && unread > 0 && <span className="badge">{unread}</span>}
      </NavLink>
    );
  };

  return (
    <div className="app-shell">
      {/* ── SIDEBAR ── */}
      <aside className={"sidebar" + (mobileOpen ? " open" : "")}>
        <div className="sidebar-brand">
          {/* Full JAIN JGi logo */}
          <svg viewBox="0 0 240 52" width="200" height="44" xmlns="http://www.w3.org/2000/svg" style={{flexShrink:0}}>
            {/* White circle */}
            <circle cx="26" cy="26" r="24" fill="#ffffff"/>
            {/* JG text in dark navy */}
            <text x="5" y="34" fontFamily="Arial Black,Arial,sans-serif" fontWeight="900" fontSize="19" fill="#0f2744">JG</text>
            {/* i stem */}
            <text x="35.5" y="34" fontFamily="Arial Black,Arial,sans-serif" fontWeight="900" fontSize="19" fill="#0f2744">i</text>
            {/* blue dot above i */}
            <circle cx="38.5" cy="13" r="3.2" fill="#2563eb"/>

            {/* JAIN large text */}
            <text x="60" y="33" fontFamily="Arial Black,Arial,sans-serif" fontWeight="900" fontSize="28" fill="#ffffff" letterSpacing="1">JAIN</text>

            {/* white rule under JAIN */}
            <rect x="60" y="37" width="20" height="2.5" fill="#ffffff"/>
            {/* DEEMED-TO-BE UNIVERSITY */}
            <text x="84" y="47" fontFamily="Arial,sans-serif" fontWeight="600" fontSize="8" fill="#ffffff" letterSpacing="0.6">DEEMED-TO-BE UNIVERSITY</text>
          </svg>
        </div>

        <nav className="side-nav">
          {mainNav.map(renderNavItem)}
        </nav>

        <div className="side-divider" />
        <div className="side-bottom">
          {bottomNav.map(renderNavItem)}
        </div>
      </aside>

      {mobileOpen && <div className="scrim" onClick={() => setMobileOpen(false)} />}

      {/* ── MAIN ── */}
      <div className="app-main">
        {/* Header */}
        <header className="app-header">
          <div className="app-header-left">
            <button className="hamburger-btn" onClick={() => setMobileOpen(v => !v)} aria-label="Menu">
              <Ic d={<><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></>} size={20} />
            </button>
            <div className="header-divider" />
            <div>
              <div className="dept-title">{branding.department_name}</div>
              <div className="dept-sub">{branding.product_name}</div>
            </div>
          </div>

          <div className="app-header-right">
            <NavLink to="/notifications" className="bell-btn" aria-label="Notifications">
              <Ic d={ICONS.bell} size={18} />
              {unread > 0 && <span className="bell-dot" />}
            </NavLink>
            <div className="user-chip">
              <span className="avatar">{initials}</span>
              <span className="user-meta">
                <span className="user-name">{user.name.replace(/\(.*?\)/g, "").trim().split(/\s+/)[0]}</span>
                <span className="user-role">{isHod ? "Administrator" : "Teacher"}</span>
              </span>
              <span className="user-caret"><Ic d={ICONS.chevronDown} size={14} /></span>
            </div>
            <button className="logout-btn" onClick={logout}>Log out</button>
          </div>
        </header>

        {/* Content */}
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
