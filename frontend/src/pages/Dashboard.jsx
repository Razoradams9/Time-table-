import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth.jsx";

/* ── inline icons ── */
const Ic = ({ d, size = 20, color }) => (
  <svg className="ic" viewBox="0 0 24 24" fill="none" stroke={color || "currentColor"}
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" width={size} height={size}>
    {d}
  </svg>
);
const IcPeople      = (p) => <Ic {...p} d={<><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></>} />;
const IcCheckCircle = (p) => <Ic {...p} d={<><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></>} />;
const IcUserX       = (p) => <Ic {...p} d={<><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="18" y1="8" x2="23" y2="13"/><line x1="23" y1="8" x2="18" y2="13"/></>} />;
const IcRepeat      = (p) => <Ic {...p} d={<><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></>} />;
const IcCalendar    = (p) => <Ic {...p} d={<><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></>} />;
const IcTimetable   = (p) => <Ic {...p} d={<><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></>} />;
const IcAddUser     = (p) => <Ic {...p} d={<><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></>} />;
const IcBook        = (p) => <Ic {...p} d={<><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></>} />;
const IcShuffle     = (p) => <Ic {...p} d={<><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/></>} />;
const IcInbox       = (p) => <Ic {...p} d={<><polyline points="22 13 16 13 14 16 10 16 8 13 2 13"/><path d="M5.45 5.11L2 13v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-7.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></>} />;
const IcStar        = (p) => <Ic {...p} d={<><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></>} />;
const IcShield      = (p) => <Ic {...p} d={<><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></>} />;
const IcFile        = (p) => <Ic {...p} d={<><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></>} />;
const IcSend        = (p) => <Ic {...p} d={<><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></>} />;
const IcTrash       = (p) => <Ic {...p} d={<><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6M10 11v6M14 11v6M9 6V4h6v2"/></>} />;

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

function timeAgo(iso) {
  const secs = Math.max(0, Math.floor((Date.now() - new Date(iso + (iso.endsWith("Z") ? "" : "Z")).getTime()) / 1000));
  if (secs < 60) return "just now";
  const m = Math.floor(secs / 60);
  if (m < 60) return `${m} mins ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} hour${h > 1 ? "s" : ""} ago`;
  return `${Math.floor(h / 24)} days ago`;
}

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/* ── Demo fallback data shown when the backend returns no records ── */
const DEMO_OVERVIEW = {
  total_teachers: 42, present_today: 38, absent_today: 4, substitutions_today: 6,
};

const DEMO_SUBS = [
  { id: 1, period: "Period 1", class_section: "S3 BCA AI",  subject: "Computer Networks", absent_teacher: "Mr. Sameeran",       substitute_teacher: "Dr. Spurgen Ratheash", status: "ASSIGNED" },
  { id: 2, period: "Period 3", class_section: "S3 BCA DA",  subject: "Database Management Systems", absent_teacher: "Dr. Nisha", substitute_teacher: "Dr. Hari Narayanan",   status: "ASSIGNED" },
  { id: 3, period: "Period 4", class_section: "S3 BCA CS",  subject: "Operating Systems", absent_teacher: "Ms. Soumya K",       substitute_teacher: "Dr. Sruthi",           status: "ASSIGNED" },
  { id: 4, period: "Period 5", class_section: "S1 BCA AI-A", subject: "Python Programming", absent_teacher: "Dr. Rajeev",       substitute_teacher: null,                   status: "UNCOVERED" },
];

const DEMO_TIMETABLE = [
  { id: 1, time: "09:00 – 10:00", cls: "S3 BCA AI",   subject: "Computer Networks", teacher: "Mr. Sameeran",        room: "Room-1",    status: "Scheduled" },
  { id: 2, time: "10:00 – 11:00", cls: "S3 BCA DA",   subject: "Database Management Systems", teacher: "Dr. Nisha", room: "Room-2",    status: "Scheduled" },
  { id: 3, time: "11:00 – 12:00", cls: "S3 BCA CS",   subject: "Operating Systems", teacher: "Ms. Soumya K",        room: "Room-3",    status: "Scheduled" },
  { id: 4, time: "12:00 – 01:00", cls: "S1 BCA AI-A", subject: "Python Programming", teacher: "TBD",                room: "Admin Lab", status: "Pending"   },
];

const now = new Date();
const ts  = (minusMinutes) => new Date(now.getTime() - minusMinutes * 60000).toISOString();
const DEMO_ACTIVITY = [
  { id: 1, action: "CREATE",   entity: "substitution", detail: "S3 BCA AI | Computer Networks | Period 1", actor: "Dr. Spurgen Ratheash", created_at: ts(10) },
  { id: 2, action: "CANCEL",   entity: "leave",        detail: "Date: " + now.toLocaleDateString("en-GB", { day:"2-digit", month:"short", year:"numeric" }), actor: "Dr. Rajeev", created_at: ts(25) },
  { id: 3, action: "CREATE",   entity: "substitution", detail: "S3 BCA DA | DBMS | Period 3",              actor: "Dr. Hari Narayanan",   created_at: ts(32) },
  { id: 4, action: "APPROVE",  entity: "timetable",    detail: "Even Semester | 2026",                     actor: null,                   created_at: ts(60) },
  { id: 5, action: "CREATE",   entity: "teacher",      detail: "Department of Computer Applications",      actor: "Mrs. Anjana Chandran", created_at: ts(180) },
];

export default function Dashboard() {
  const { user, branding } = useAuth();
  const navigate = useNavigate();
  const isHod = user.role === "HOD";

  const [overview,      setOverview]      = useState(null);
  const [subs,          setSubs]          = useState([]);
  const [entries,       setEntries]       = useState([]);
  const [slots,         setSlots]         = useState([]);
  const [activity,      setActivity]      = useState([]);
  const [loading,       setLoading]       = useState(true);
  const [unread,        setUnread]        = useState(0);
  const [demoTimetable, setDemoTimetable] = useState(false);

  const today    = new Date();
  const todayStr = today.toISOString().slice(0, 10);
  const todayDow = (today.getDay() + 6) % 7;

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true);
      try {
        const tasks = [api.substitutions(todayStr), api.activeTimetable(), api.timeSlots()];
        if (isHod) tasks.push(api.overview(todayStr), api.activity(6), api.unreadCount());
        const [sub, ent, sl, ov, act, uc] = await Promise.all(tasks);
        if (!alive) return;
        setSubs(sub?.length       ? sub : DEMO_SUBS);
        setEntries(ent);
        setSlots(sl);
        // if no timetable entries exist for today, flag demo mode
        const todayEntries = ent.filter(e => e.time_slot.day_of_week === ((today.getDay() + 6) % 7));
        if (todayEntries.length === 0) setDemoTimetable(true);
        if (isHod) {
          setOverview(ov);
          setActivity(act?.length ? act : DEMO_ACTIVITY);
          setUnread(uc?.unread || 0);
        }
      } finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [isHod, todayStr]);

  const firstName = user.name.replace(/\(.*?\)/g, "").trim().split(/\s+/)[0];
  const dateLabel = today.toLocaleDateString("en-US", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  const todaysClasses = entries
    .filter(e => e.time_slot.day_of_week === todayDow)
    .sort((a, b) => a.time_slot.period_index - b.time_slot.period_index);

  // Use demo overview if real data shows all-zeros (no seed data for today)
  const displayOverview = overview && (overview.total_teachers > 0) ? overview : DEMO_OVERVIEW;

  return (
    <>
      {/* WELCOME CARD */}
      <div className="card welcome-card">
        <div>
          <div className="welcome-title">{greeting()}, {firstName}! <span className="wave">👋</span></div>
          <div className="welcome-sub">Here's what's happening in your department today.</div>
        </div>
        <div className="welcome-date">
          <div className="date-main">
            <IcCalendar size={16} />
            {dateLabel}
          </div>
          <div className="date-sub">{branding.semester_label}</div>
        </div>
      </div>

      {/* STAT CARDS */}
      {isHod && (
        <div className="stat-row">
          <StatCard tone="blue"   Icon={IcPeople}      value={loading ? "—" : displayOverview.total_teachers}      label="Total Teachers"  onClick={() => navigate("/teachers")} />
          <StatCard tone="green"  Icon={IcCheckCircle} value={loading ? "—" : displayOverview.present_today}       label="Present Today" />
          <StatCard tone="red"    Icon={IcUserX}       value={loading ? "—" : displayOverview.absent_today}        label="Absent Today"    onClick={() => navigate("/leaves")} />
          <StatCard tone="purple" Icon={IcRepeat}      value={loading ? "—" : displayOverview.substitutions_today} label="Substitutions"   onClick={() => navigate("/substitutions")} />
        </div>
      )}

      {/* 3-COLUMN GRID */}
      <div className="dash-grid">

        {/* LEFT: mail panel */}
        <div className="dash-left">
          <div className="mail-panel">
            <div className="mail-compose">
              <button className="mail-compose-btn">Compose</button>
            </div>
            <div className="mail-nav">
              {[
                { icon: IcInbox,  label: "Inbox",     count: unread, active: true },
                { icon: IcStar,   label: "Starred" },
                { icon: IcShield, label: "Important" },
                { icon: IcFile,   label: "Draft" },
                { icon: IcSend,   label: "Sent Mail" },
                { icon: IcTrash,  label: "Trash" },
              ].map(({ icon: Icon, label, count, active }) => (
                <div key={label} className={"mail-item" + (active ? " active" : "")}>
                  <Icon size={14} />
                  <span>{label}</span>
                  {count > 0 && <span className="mail-count">{count}</span>}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* MIDDLE: substitutions + timetable */}
        <div className="dash-middle">
          {/* Today's Substitutions */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-head">
              <h2>Today's Substitutions</h2>
              {isHod && <Link to="/substitutions" className="view-all">View all →</Link>}
            </div>
            {loading ? <SkeletonTable /> : subs.length === 0 ? (
              <div className="empty-state">No substitutions scheduled for today.</div>
            ) : (
              <div className="tbl-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Period</th><th>Class</th><th>Subject</th>
                      <th>Absent Teacher</th><th>Assigned To</th><th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {subs.map(s => (
                      <tr key={s.id}>
                        <td>{s.period.split(" ")[0]}</td>
                        <td>{s.class_section}</td>
                        <td>{s.subject}</td>
                        <td>{s.absent_teacher}</td>
                        <td>{s.substitute_teacher || "—"}</td>
                        <td>
                          {s.status === "ASSIGNED"
                            ? <span className="pill green">Assigned</span>
                            : <span className="pill red">Unassigned</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Today's Timetable */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-head">
              <h2>Today's Timetable</h2>
              <Link to="/timetable" className="view-all">View full timetable →</Link>
            </div>
            {loading ? <SkeletonTable /> : demoTimetable ? (
              <div className="tbl-wrap">
                <table>
                  <thead>
                    <tr><th>Time</th><th>Class</th><th>Subject</th><th>Teacher</th><th>Room</th><th>Status</th></tr>
                  </thead>
                  <tbody>
                    {DEMO_TIMETABLE.map(e => (
                      <tr key={e.id}>
                        <td>{e.time}</td>
                        <td>{e.cls}</td>
                        <td>{e.subject}</td>
                        <td>{e.teacher}</td>
                        <td>{e.room}</td>
                        <td>
                          {e.status === "Scheduled"
                            ? <span className="pill blue">Scheduled</span>
                            : <span className="pill amber">Pending</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : todaysClasses.length === 0 ? (
              <div className="empty-state">No classes scheduled for today ({DAYS[todayDow]}).</div>
            ) : (
              <div className="tbl-wrap">
                <table>
                  <thead>
                    <tr><th>Time</th><th>Class</th><th>Subject</th><th>Teacher</th><th>Room</th><th>Status</th></tr>
                  </thead>
                  <tbody>
                    {todaysClasses.map(e => (
                      <tr key={e.id}>
                        <td>{e.time_slot.start_time} – {e.time_slot.end_time}</td>
                        <td>{e.class_section.name}</td>
                        <td>{e.subject.name}</td>
                        <td>{e.teacher.name}</td>
                        <td>{e.room.name}</td>
                        <td><span className="pill blue">Scheduled</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT: quick actions + activity */}
        <div className="dash-right">
          {isHod && (
            <div className="card" style={{ marginBottom: 0 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--gray-600)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 12 }}>
                Quick Actions
              </div>
              <div className="quick-grid">
                <QuickBtn Icon={IcTimetable} label="Create Timetable"      onClick={() => navigate("/timetable")} />
                <QuickBtn Icon={IcAddUser}   label="Add Teacher"           onClick={() => navigate("/teachers")} />
                <QuickBtn Icon={IcBook}      label="Add Subject"           disabled />
                <QuickBtn Icon={IcShuffle}   label="Manage Substitutions"  onClick={() => navigate("/substitutions")} highlight />
              </div>
            </div>
          )}

          {isHod && (
            <div className="card" style={{ marginBottom: 0 }}>
              <div className="card-head">
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--gray-600)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Recent Activity
                </div>
                <Link to="/substitutions" className="view-all">View all →</Link>
              </div>
              {loading ? <SkeletonActivity /> : activity.length === 0 ? (
                <div className="empty-state" style={{ padding: "16px 0" }}>No recent activity.</div>
              ) : (
                <ul className="activity-feed">
                  {activity.map(a => (
                    <li key={a.id} className="activity-item">
                      <span className={"act-dot " + dotTone(a)} />
                      <div className="act-body">
                        <div className="act-title">{humanAction(a)}</div>
                        <div className="act-detail">{a.detail}</div>
                        <div className="act-time">{timeAgo(a.created_at)}</div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {!isHod && (
            <div className="card" style={{ marginBottom: 0 }}>
              <div style={{ fontWeight: 700, marginBottom: 8 }}>Your Day</div>
              <p style={{ fontSize: 13, color: "var(--gray-500)", marginBottom: 14 }}>
                {todaysClasses.length} class{todaysClasses.length !== 1 ? "es" : ""} scheduled today.
              </p>
              <Link to="/leaves"><button style={{ width: "100%" }}>Register a Leave</button></Link>
            </div>
          )}
        </div>

      </div>
    </>
  );
}

/* ── Sub-components ── */

function StatCard({ tone, Icon, value, label, onClick }) {
  return (
    <div className="stat-card" onClick={onClick} role={onClick ? "button" : undefined} tabIndex={onClick ? 0 : undefined}>
      <div className={"stat-icon-wrap " + tone}><Icon size={22} /></div>
      <div className="stat-body">
        <div className={"stat-num " + (tone === "blue" ? "" : tone)}>{value}</div>
        <div className="stat-lbl">{label}</div>
      </div>
      {onClick && <span className="stat-arrow">›</span>}
    </div>
  );
}

function QuickBtn({ Icon, label, onClick, disabled, highlight }) {
  return (
    <button
      className={"quick-btn" + (highlight ? " highlight" : "")}
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      style={disabled ? { opacity: 0.45 } : undefined}
    >
      <span className="qa-icon"><Icon size={20} /></span>
      <span>{label}</span>
    </button>
  );
}

function SkeletonTable() {
  return (
    <div>
      {[80, 65, 72, 58].map((w, i) => (
        <div key={i} className="skeleton skeleton-row" style={{ width: `${w}%` }} />
      ))}
    </div>
  );
}

function SkeletonActivity() {
  return (
    <div>
      {[90, 70, 80, 60, 75].map((w, i) => (
        <div key={i} className="skeleton skeleton-row" style={{ width: `${w}%` }} />
      ))}
    </div>
  );
}

function dotTone(a) {
  if (a.action === "CANCEL")               return "red";    // absent
  if (a.action === "CREATE" && a.entity === "substitution") return "green"; // assigned
  if (a.action === "CREATE" && a.entity === "teacher")      return "green"; // added
  if (a.action === "APPROVE" || a.action === "GENERATE")    return "blue";  // published
  if (a.action === "OVERRIDE")             return "purple";
  return "blue";
}

function humanAction(a) {
  const map = {
    GENERATE: "Timetable generated",
    APPROVE:  "New timetable published",
    CANCEL:   "Teacher marked absent",
    OVERRIDE: "Substitution reassigned",
  };
  if (a.action === "CREATE") {
    if (a.entity === "substitution") return `Substitute assigned: ${a.actor || ""}`;
    if (a.entity === "teacher")      return `Teacher added: ${a.actor || ""}`;
    return `${a.entity[0].toUpperCase() + a.entity.slice(1)} added`;
  }
  if (a.action === "CANCEL") return `Teacher marked absent: ${a.actor || ""}`;
  const base = map[a.action] || `${a.action} ${a.entity}`;
  return base;
}
