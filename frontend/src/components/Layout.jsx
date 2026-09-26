import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth.jsx";

// Simple inline line-icons (1.5–2px stroke), mono-tone, per the design guide.
const Icon = ({ path, filled }) => (
  <svg
    className="ic"
    viewBox="0 0 24 24"
    fill={filled ? "currentColor" : "none"}
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    {path}
  </svg>
);
const icons = {
  dashboard: <><rect x="3" y="3" width="7" height="9" /><rect x="14" y="3" width="7" height="5" /><rect x="14" y="12" width="7" height="9" /><rect x="3" y="16" width="7" height="5" /></>,
  timetable: <><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M3 10h18M8 2v4M16 2v4" /></>,
  teachers: <><circle cx="9" cy="7" r="3" /><path d="M2 21v-2a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v2M17 11l2 2 4-4" /></>,
  classes: <><path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6" /></>,
  subjects: <><path d="M4 4h11a2 2 0 0 1 2 2v14H6a2 2 0 0 1-2-2zM17 6h3v14H8" /></>,
  substitutions: <><path d="M4 7h13l-3-3M20 17H7l3 3" /></>,
  attendance: <><rect x="3" y="4" width="18" height="18" rx="2" /><path d="m9 14 2 2 4-4" /></>,
  messages: <><path d="M4 4h16v12H7l-3 3z" /></>,
  reports: <><path d="M4 20V10M10 20V4M16 20v-8M22 20H2" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M19 12a7 7 0 0 0-.1-1l2-1.6-2-3.4-2.4 1a7 7 0 0 0-1.7-1L14.5 2h-5l-.3 2.6a7 7 0 0 0-1.7 1l-2.4-1-2 3.4 2 1.6a7 7 0 0 0 0 2l-2 1.6 2 3.4 2.4-1a7 7 0 0 0 1.7 1L9.5 22h5l.3-2.6a7 7 0 0 0 1.7-1l2.4 1 2-3.4-2-1.6a7 7 0 0 0 .1-1z" /></>,
  help: <><circle cx="12" cy="12" r="9" /><path d="M9.5 9a2.5 2.5 0 0 1 4.5 1.5c0 1.5-2 2-2 3.5M12 17h.01" /></>,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0" /></>,
};

export default function Layout() {
  const { user, logout, branding } = useAuth();
  const [unread, setUnread] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);
  const isHod = user.role === "HOD";
  const location = useLocation();

  useEffect(() => {
    let alive = true;
    async function poll() {
      try {
        const r = await api.unreadCount();
        if (alive) setUnread(r.unread);
      } catch {
        /* ignore */
      }
    }
    poll();
    const t = setInterval(poll, 15000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  // Close the mobile drawer on route change.
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const initials = user.name
    .replace(/\(.*?\)/g, "")
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();

  const link = ({ isActive }) => "side-link" + (isActive ? " active" : "");

  // Nav items. `soon` = placeholder (feature not yet wired to backend).
  const mainNav = [
    { to: "/", icon: "dashboard", label: "Dashboard", end: true },
    { to: "/timetable", icon: "timetable", label: "Timetable" },
    { to: "/teachers", icon: "teachers", label: "Teachers", hod: true },
    { to: "/classes", icon: "classes", label: "Classes", hod: true, soon: true },
    { to: "/subjects", icon: "subjects", label: "Subjects", hod: true, soon: true },
    { to: "/substitutions", icon: "substitutions", label: "Substitutions", hod: true },
    { to: "/attendance", icon: "attendance", label: "Attendance", soon: true },
    { to: "/leaves", icon: "attendance", label: "Leaves" },
    { to: "/notifications", icon: "messages", label: "Messages" },
    { to: "/fairness", icon: "reports", label: "Reports", hod: true },
  ];
  const bottomNav = [
    { to: "/settings", icon: "settings", label: "Settings", soon: true },
    { to: "/help", icon: "help", label: "Help", soon: true },
  ];

  const renderLink = (item) => {
    if (item.hod && !isHod) return null;
    if (item.soon) {
      return (
        <span key={item.label} className="side-link soon" title="Coming soon">
          <Icon path={icons[item.icon]} />
          <span>{item.label}</span>
          <span className="soon-dot">soon</span>
        </span>
      );
    }
    return (
      <NavLink key={item.label} to={item.to} end={item.end} className={link}>
        <Icon path={icons[item.icon]} />
        <span>{item.label}</span>
        {item.label === "Messages" && unread > 0 && <span className="badge">{unread}</span>}
      </NavLink>
    );
  };

  return (
    <div className="app-shell">
      <aside className={"sidebar" + (mobileOpen ? " open" : "")}>
        <div className="sidebar-brand">
          <span className="logo-badge">JGi</span>
          <div className="logo-text">
            <span className="logo-name">{branding.institution_name}</span>
            <span className="logo-sub">{branding.institution_subtitle}</span>
          </div>
        </div>
        <nav className="side-nav">{mainNav.map(renderLink)}</nav>
        <div className="side-nav side-bottom">{bottomNav.map(renderLink)}</div>
      </aside>

      {mobileOpen && <div className="scrim" onClick={() => setMobileOpen(false)} />}

      <div className="app-main">
        <header className="app-header">
          <div className="app-header-left">
            <button className="ghost small hamburger" onClick={() => setMobileOpen((v) => !v)} aria-label="Menu">
              ☰
            </button>
            <div>
              <div className="dept-title">{branding.department_name}</div>
              <div className="dept-sub">{branding.product_name}</div>
            </div>
          </div>
          <div className="app-header-right">
            <NavLink to="/notifications" className="bell" aria-label="Notifications">
              <Icon path={icons.bell} />
              {unread > 0 && <span className="bell-dot" />}
            </NavLink>
            <div className="user-chip">
              <span className="avatar">{initials}</span>
              <span className="user-meta">
                <span className="user-name">{user.name}</span>
                <span className="user-role">{isHod ? "Administrator" : "Teacher"}</span>
              </span>
            </div>
            <button className="ghost small" onClick={logout}>
              Log out
            </button>
          </div>
        </header>
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
