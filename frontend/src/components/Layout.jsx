import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import { Icon, icons } from "./Icons.jsx";

export default function Layout() {
  const { user, branding, logout } = useAuth();
  const [unread, setUnread] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const isHod = user.role === "HOD";
  const location = useLocation();
  const navigate = useNavigate();

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
    setMenuOpen(false);
  }, [location.pathname]);

  // Close the user menu on outside click or Escape.
  useEffect(() => {
    if (!menuOpen) return undefined;
    function onDown(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    }
    function onKey(e) {
      if (e.key === "Escape") setMenuOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  function onLogout() {
    setMenuOpen(false);
    logout();
    navigate("/login", { replace: true });
  }

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
  const liveNav = [
    { to: "/", icon: "dashboard", label: "Dashboard", end: true },
    { to: "/timetable", icon: "timetable", label: "Timetable" },
    { to: "/courses", icon: "subjects", label: "Courses" },
    { to: "/teachers", icon: "teachers", label: "Teachers", hod: true },
    { to: "/substitutions", icon: "substitutions", label: "Substitutions", hod: true },
    { to: "/leaves", icon: "leaves", label: "Leaves" },
    { to: "/compensations", icon: "substitutions", label: "Compensations" },
    { to: "/notifications", icon: "messages", label: "Messages" },
    { to: "/fairness", icon: "reports", label: "Reports", hod: true },
  ];
  const teacherNav = [
    { to: "/", icon: "dashboard", label: "Dashboard", end: true },
    { to: "/timetable", icon: "timetable", label: "My Timetable" },
    { to: "/courses", icon: "subjects", label: "Courses" },
    { to: "/leaves", icon: "leaves", label: "Leaves" },
    { to: "/compensations", icon: "substitutions", label: "Make-ups" },
    { to: "/notifications", icon: "messages", label: "Messages" },
  ];
  const bottomNav = [
    { to: "/help", icon: "help", label: "Help & Support" },
  ];

  const renderLink = (item) => {
    if (item.hod && !isHod) return null;
    if (item.soon) {
      return (
        <span key={item.label} className="side-link soon" title="Coming soon">
          <Icon path={icons[item.icon]} />
          <span>{item.label}</span>
          <span className="soon-dot">Soon</span>
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
    <div className={"app-shell" + (isHod ? "" : " teacher-portal")}>
      <header className="app-header">
        <div className="app-header-left">
          <button
            type="button"
            className="hamburger"
            onClick={() => setMobileOpen((v) => !v)}
            aria-label="Toggle menu"
            aria-expanded={mobileOpen}
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
              <path d="M4 7h16M4 12h16M4 17h16" />
            </svg>
          </button>
          <Link to="/" className="brand-link" aria-label="Go to dashboard">
            <img className="brand-logo" src="/jain-logo-light.png" alt="Jain Deemed-to-be University, Kochi" />
          </Link>
          <div className="dept-block">
            <div className="dept-label">
              {branding.product_name}
              {!isHod && <span className="portal-pill">Teacher portal</span>}
            </div>
            <h1 className="dept-title">{branding.department_name}</h1>
          </div>
        </div>
        <div className="app-header-right">
          <NavLink
            to="/notifications"
            className="bell"
            aria-label={unread > 0 ? `Notifications, ${unread} unread` : "Notifications"}
          >
            <Icon path={icons.bell} />
            {unread > 0 && <span className="bell-dot" />}
          </NavLink>
          <div className="user-menu" ref={menuRef}>
            <button
              type="button"
              className="user-chip user-chip-btn"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((v) => !v)}
            >
              <span className="avatar" aria-hidden="true">{initials}</span>
              <span className="user-meta">
                <span className="user-name">{user.name}</span>
                <span className="user-role">{isHod ? "Administrator" : "Teacher"}</span>
              </span>
              <span className="sr-only">Account menu</span>
            </button>
            {menuOpen && (
              <div className="user-menu-list" role="menu">
                <Link to="/change-password" role="menuitem" className="user-menu-item">
                  <Icon path={icons.lock} />
                  <span>Change password</span>
                </Link>
                <button type="button" role="menuitem" className="user-menu-item" onClick={onLogout}>
                  <Icon path={icons.logout} />
                  <span>Log out</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="app-body">
        <aside className={"sidebar" + (mobileOpen ? " open" : "")}>
          <nav className="side-nav" aria-label="Main">
            {(isHod ? liveNav : teacherNav).map(renderLink)}
          </nav>
          <div className="side-nav side-bottom">{bottomNav.map(renderLink)}</div>
        </aside>

        {mobileOpen && <div className="scrim" onClick={() => setMobileOpen(false)} />}

        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
