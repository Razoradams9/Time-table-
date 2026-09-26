import { useState } from "react";
import { useNavigate } from "react-router-dom";

/* ── Inline SVG icon helper ── */
const Ic = ({ d, size = 16, color }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke={color || "currentColor"}
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
    width={size} height={size} style={{ display: "inline-block", verticalAlign: "middle", flexShrink: 0 }}>
    {d}
  </svg>
);
const IcRepeat    = (p) => <Ic {...p} d={<><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></>} />;
const IcCheck     = (p) => <Ic {...p} d={<><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></>} />;
const IcAlert     = (p) => <Ic {...p} d={<><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></>} />;
const IcUsers     = (p) => <Ic {...p} d={<><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></>} />;
const IcCalendar  = (p) => <Ic {...p} d={<><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></>} />;
const IcEye       = (p) => <Ic {...p} d={<><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></>} />;
const IcPlay      = (p) => <Ic {...p} d={<><polygon points="5 3 19 12 5 21 5 3"/></>} />;
const IcX         = (p) => <Ic {...p} d={<><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></>} />;
const IcRefresh   = (p) => <Ic {...p} d={<><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></>} />;
const IcUserPlus  = (p) => <Ic {...p} d={<><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></>} />;
const IcChevDown  = (p) => <Ic {...p} d={<><polyline points="6 9 12 15 18 9"/></>} />;
const IcCheckFill = (p) => <Ic {...p} d={<><circle cx="12" cy="12" r="10" fill="currentColor" stroke="none"/><polyline points="9 12 11 14 15 10" stroke="#fff" strokeWidth="2" fill="none"/></>} />;
const IcClock     = (p) => <Ic {...p} d={<><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></>} />;
const IcMapPin    = (p) => <Ic {...p} d={<><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></>} />;
const IcUser      = (p) => <Ic {...p} d={<><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></>} />;
const IcBook      = (p) => <Ic {...p} d={<><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></>} />;

/* ── Demo data ── */
const INITIAL_SUBS = [
  { id: 1, period: "1", time: "09:00 - 10:00", cls: "BCA AI - A", subject: "Python",            absent: "Rahul Kumar",  assigned: "Anu Thomas",   status: "ASSIGNED" },
  { id: 2, period: "2", time: "10:00 - 11:00", cls: "BCA AI - B", subject: "DBMS",              absent: "Sarah Joseph", assigned: "Vijay Sanker", status: "ASSIGNED" },
  { id: 3, period: "3", time: "11:00 - 12:00", cls: "BCA - C",    subject: "Operating Systems", absent: "Meera Nair",   assigned: "Arun Prasad",  status: "ASSIGNED" },
  { id: 4, period: "4", time: "12:00 - 01:00", cls: "BCA AI - A", subject: "Computer Networks", absent: "Akhil Raj",    assigned: "Priya Menon",  status: "ASSIGNED" },
  { id: 5, period: "5", time: "02:00 - 03:00", cls: "BCA - B",    subject: "Java",               absent: "Nikhil Varma", assigned: null,           status: "UNASSIGNED" },
  { id: 6, period: "6", time: "03:00 - 04:00", cls: "BCA AI - C", subject: "Database",           absent: "Fahad Ali",   assigned: "Sneha Ravi",   status: "ASSIGNED" },
];

const FREE_TEACHERS = [
  { id: 1, name: "Priya Menon",  dept: "BCA", currentPeriod: "Free",         status: "Available", auto: true },
  { id: 2, name: "Arun Prasad",  dept: "BCA", currentPeriod: "Class in 5th", status: "Busy",      auto: false },
  { id: 3, name: "Anu Thomas",   dept: "BCA", currentPeriod: "Free",         status: "Available", auto: false },
  { id: 4, name: "Vijay Sanker", dept: "BCA", currentPeriod: "Lab Duty",     status: "Busy",      auto: false },
  { id: 5, name: "Sneha Ravi",   dept: "BCA", currentPeriod: "Free",         status: "Available", auto: false },
];

const INITIAL_ACTIVITY = [
  { id: 1, tone: "green", title: "Substitute assigned: Anu Thomas",   detail: "BCA AI - A | Python | Period 1",   time: "10 mins ago" },
  { id: 2, tone: "green", title: "Substitute assigned: Vijay Sanker", detail: "BCA AI - B | DBMS | Period 2",     time: "25 mins ago" },
  { id: 3, tone: "green", title: "Substitute assigned: Arun Prasad",  detail: "BCA - C | OS | Period 3",          time: "32 mins ago" },
  { id: 4, tone: "red",   title: "Teacher marked absent: Nikhil Varma",detail: "BCA - B | Java | Period 5",       time: "1 hour ago" },
  { id: 5, tone: "green", title: "Substitute assigned: Sneha Ravi",   detail: "BCA AI - C | Database | Period 6", time: "1 hour ago" },
];

/* Auto-assign steps */
const STEPS = [
  { label: "Absence Detected",           desc: "Nikhil Varma is marked absent for Period 5 (02:00 - 03:00)" },
  { label: "Finding Available Teachers", desc: "Checking teachers who are free during this period..." },
  { label: "Filtering Conflicts",        desc: "Excluding teachers who are already assigned or absent..." },
  { label: "Selecting Teacher",          desc: "Found 3 available teachers. Selecting the first available..." },
  { label: "Assigning Class",            desc: "Assigning Java (BCA - B) to Priya Menon..." },
  { label: "Completed",                  desc: "Updating timetable and notifying teacher..." },
];

export default function Substitutions() {
  const navigate = useNavigate();

  const [subs,         setSubs]         = useState(INITIAL_SUBS);
  const [activity,     setActivity]     = useState(INITIAL_ACTIVITY);
  const [drawerOpen,   setDrawerOpen]   = useState(false);
  const [stepsDone,    setStepsDone]    = useState(0);   // 0 = not started, 1-6 = steps complete
  const [assigned,     setAssigned]     = useState(false);
  const [selectedTeacher, setSelectedTeacher] = useState(1); // Priya Menon pre-selected
  const [activeTab,    setActiveTab]    = useState("today");
  const [filterCls,    setFilterCls]    = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [animating,    setAnimating]    = useState(false);

  /* counts */
  const total      = subs.length;
  const assignedN  = subs.filter(s => s.status === "ASSIGNED").length;
  const unassigned = subs.filter(s => s.status === "UNASSIGNED").length;
  const absent     = 4; // fixed demo

  /* filter rows */
  const visible = subs.filter(s => {
    if (filterCls !== "all" && s.cls !== filterCls) return false;
    if (filterStatus !== "all" && s.status !== filterStatus) return false;
    return true;
  });

  /* open drawer and run animation */
  function openAutoAssign() {
    setDrawerOpen(true);
    setStepsDone(0);
    setAssigned(false);
    setAnimating(true);
    let step = 0;
    const interval = setInterval(() => {
      step += 1;
      setStepsDone(step);
      if (step >= STEPS.length) {
        clearInterval(interval);
        setAnimating(false);
        setAssigned(true);
        // update table
        setSubs(prev => prev.map(s =>
          s.id === 5 ? { ...s, status: "ASSIGNED", assigned: "Priya Menon" } : s
        ));
        // add activity
        setActivity(prev => [
          { id: Date.now(), tone: "green", title: "Substitute assigned: Priya Menon",
            detail: "BCA - B | Java | Period 5", time: "just now" },
          ...prev,
        ]);
      }
    }, 700);
  }

  function handleAssignSelected() {
    if (!assigned) openAutoAssign();
  }

  const classes  = ["all", ...new Set(INITIAL_SUBS.map(s => s.cls))];
  const statuses = ["all", "ASSIGNED", "UNASSIGNED"];

  return (
    <div className="subs-page">
      {/* ── PAGE HEADER ── */}
      <div className="subs-header">
        <div>
          <h1 className="subs-title">Substitutions</h1>
          <p className="subs-subtitle">Automatically assign classes when a teacher is absent.</p>
        </div>
        <div className="subs-header-right">
          <div className="date-chip">
            <IcCalendar size={15} />
            <span>Thursday, 24 September 2026</span>
            <IcChevDown size={14} />
          </div>
          <button className="btn-mark-absence" onClick={() => {}}>
            <IcUserPlus size={16} />
            Mark Absence
          </button>
        </div>
      </div>

      {/* ── STAT CARDS ── */}
      <div className="subs-stats">
        <StatCard tone="purple" Icon={IcRepeat}  value={total}      label="Total Substitutions" />
        <StatCard tone="green"  Icon={IcCheck}   value={assignedN}  label="Assigned" />
        <StatCard tone="red"    Icon={IcAlert}   value={unassigned} label="Unassigned" />
        <StatCard tone="blue"   Icon={IcUsers}   value={absent}     label="Teachers Absent" />
      </div>

      {/* ── MAIN CARD ── */}
      <div className="card subs-main-card">
        {/* Tabs */}
        <div className="subs-tabs">
          {[["today", "Today's Substitutions"], ["all", "All Substitutions"], ["requests", "Absence Requests"]].map(([key, label]) => (
            <button key={key} className={"subs-tab" + (activeTab === key ? " active" : "")} onClick={() => setActiveTab(key)}>
              {label}
            </button>
          ))}
        </div>

        {/* Filters */}
        <div className="subs-filters">
          <div className="filter-group">
            <label>Select Date</label>
            <div className="filter-select-wrap">
              <IcCalendar size={14} />
              <select defaultValue="today"><option>24 Sep 2026</option></select>
            </div>
          </div>
          <div className="filter-group">
            <label>Class</label>
            <div className="filter-select-wrap">
              <select value={filterCls} onChange={e => setFilterCls(e.target.value)}>
                {classes.map(c => <option key={c} value={c}>{c === "all" ? "All Classes" : c}</option>)}
              </select>
            </div>
          </div>
          <div className="filter-group">
            <label>Subject</label>
            <div className="filter-select-wrap">
              <select defaultValue="all"><option value="all">All Subjects</option></select>
            </div>
          </div>
          <div className="filter-group">
            <label>Status</label>
            <div className="filter-select-wrap">
              <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
                {statuses.map(s => <option key={s} value={s}>{s === "all" ? "All Status" : s[0] + s.slice(1).toLowerCase()}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="tbl-wrap">
          <table className="subs-table">
            <thead>
              <tr>
                <th>#</th><th>Period</th><th>Class</th><th>Subject</th>
                <th>Absent Teacher</th><th>Assigned To</th><th>Status</th><th>Action</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((s, i) => (
                <tr key={s.id} className={s.status === "UNASSIGNED" ? "row-unassigned" : ""}>
                  <td className="td-num">{i + 1}</td>
                  <td>
                    <div className="td-period">{s.period}</div>
                    <div className="td-time">{s.time}</div>
                  </td>
                  <td><span className="td-cls">{s.cls}</span></td>
                  <td>{s.subject}</td>
                  <td>
                    <div className="teacher-cell">
                      <span className="teacher-avatar-sm">{s.absent[0]}</span>
                      {s.absent}
                    </div>
                  </td>
                  <td>
                    {s.assigned
                      ? <div className="teacher-cell"><span className="teacher-avatar-sm assigned">{s.assigned[0]}</span>{s.assigned}</div>
                      : <span style={{ color: "var(--gray-400)" }}>—</span>}
                  </td>
                  <td>
                    {s.status === "ASSIGNED"
                      ? <span className="pill green">Assigned</span>
                      : <span className="pill red">Unassigned</span>}
                  </td>
                  <td>
                    {s.status === "ASSIGNED"
                      ? <button className="btn-view" onClick={() => setDrawerOpen(true)}><IcEye size={13} /> View</button>
                      : <button className="btn-auto-assign" onClick={openAutoAssign}><IcPlay size={13} /> Auto Assign</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── BOTTOM GRID: activity + free teachers ── */}
      <div className="subs-bottom-grid">
        {/* Recent Activity */}
        <div className="card subs-activity-card">
          <div className="card-head">
            <h2>Recent Activity</h2>
            <span className="view-all">View all →</span>
          </div>
          <ul className="activity-feed">
            {activity.map(a => (
              <li key={a.id} className="activity-item">
                <span className={"act-dot " + a.tone} />
                <div className="act-body">
                  <div className="act-title">{a.title}</div>
                  <div className="act-detail">{a.detail}</div>
                  <div className="act-time">{a.time}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* Free Teachers */}
        <div className="card subs-free-card">
          <div className="card-head">
            <h2>Teachers Currently Free <span className="period-badge">(Period 5)</span></h2>
            <button className="btn-refresh" onClick={() => {}}><IcRefresh size={14} /> Refresh</button>
          </div>
          <div className="tbl-wrap">
            <table className="free-table">
              <thead>
                <tr><th></th><th>Name</th><th>Department</th><th>Current Period</th><th>Status</th></tr>
              </thead>
              <tbody>
                {FREE_TEACHERS.map(t => (
                  <tr key={t.id}>
                    <td>
                      <input
                        type="checkbox"
                        className="subs-checkbox"
                        checked={selectedTeacher === t.id}
                        onChange={() => setSelectedTeacher(t.id)}
                        disabled={t.status === "Busy"}
                      />
                    </td>
                    <td className={t.auto ? "teacher-name-auto" : ""}>{t.name}</td>
                    <td>{t.dept}</td>
                    <td>{t.currentPeriod}</td>
                    <td>
                      {t.status === "Available"
                        ? <span className="pill green">Available</span>
                        : <span className="pill red">Busy</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button className="btn-assign-selected" onClick={handleAssignSelected}>
            Assign Selected Teacher
          </button>
        </div>
      </div>

      {/* ── RIGHT DRAWER ── */}
      {drawerOpen && (
        <>
          <div className="drawer-scrim" onClick={() => setDrawerOpen(false)} />
          <div className="drawer">
            <div className="drawer-header">
              <span className="drawer-title">Auto Assign Substitution</span>
              <button className="drawer-close" onClick={() => setDrawerOpen(false)}><IcX size={18} /></button>
            </div>

            {/* Steps timeline */}
            <div className="drawer-section">
              <div className="steps-timeline">
                {STEPS.map((step, i) => {
                  const done    = stepsDone > i;
                  const active  = stepsDone === i && animating;
                  const pending = stepsDone < i && !done;
                  return (
                    <div key={i} className={"step-item" + (done ? " done" : active ? " active" : " pending")}>
                      <div className="step-indicator">
                        {done
                          ? <span className="step-icon done"><IcCheckFill size={18} color="var(--blue)" /></span>
                          : <span className={"step-num" + (active ? " active" : "")}>{i + 1}</span>}
                        {i < STEPS.length - 1 && <div className={"step-line" + (done ? " done" : "")} />}
                      </div>
                      <div className="step-body">
                        <div className="step-label">{step.label}</div>
                        <div className="step-desc">{step.desc}</div>
                        {active && <div className="step-spinner" />}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Assignment details */}
            <div className="drawer-section">
              <div className="assign-details-title">Assignment Details</div>
              <div className="assign-details">
                {[
                  [IcBook,     "Class",         "BCA - B"],
                  [IcBook,     "Subject",        "Java"],
                  [IcClock,    "Period",          "5 (02:00 - 03:00)"],
                  [IcMapPin,   "Room",            "TBD"],
                  [IcUser,     "Absent Teacher",  "Nikhil Varma"],
                  [IcUser,     "Assigned To",     assigned ? "Priya Menon" : "—"],
                ].map(([Icon, label, val]) => (
                  <div key={label} className="assign-row">
                    <span className="assign-icon"><Icon size={14} /></span>
                    <span className="assign-label">{label}</span>
                    <span className="assign-val">{val}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Success card */}
            {assigned && (
              <div className="drawer-section">
                <div className="success-card">
                  <div className="success-icon"><IcCheck size={20} color="#16a34a" /></div>
                  <div>
                    <div className="success-title">Class Assigned Successfully!</div>
                    <div className="success-body">Priya Menon has been assigned to BCA - B (Java) for Period 5.</div>
                    <div className="success-meta">24 Sep 2026, 10:45 AM</div>
                  </div>
                </div>
                <button className="btn-view-tt" onClick={() => { setDrawerOpen(false); navigate("/timetable"); }}>
                  View Updated Timetable
                </button>
                <button className="btn-close-drawer" onClick={() => setDrawerOpen(false)}>Close</button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({ tone, Icon, value, label }) {
  return (
    <div className={"subs-stat-card " + tone}>
      <div className={"stat-icon-wrap " + tone}><Icon size={22} /></div>
      <div className="stat-body">
        <div className={"stat-num " + (tone === "blue" ? "" : tone)}>{value}</div>
        <div className="stat-lbl">{label}</div>
      </div>
      <span className="stat-arrow">›</span>
    </div>
  );
}
