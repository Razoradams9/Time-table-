import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import { SkeletonStats, SkeletonRows } from "../components/Skeleton.jsx";
import { Icon, icons } from "../components/Icons.jsx";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function timeAgo(iso) {
  const then = new Date(iso + (iso.endsWith("Z") ? "" : "Z")).getTime();
  const secs = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (secs < 60) return "just now";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins} min${mins > 1 ? "s" : ""} ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hour${hrs > 1 ? "s" : ""} ago`;
  const days = Math.floor(hrs / 24);
  return `${days} day${days > 1 ? "s" : ""} ago`;
}

export default function Dashboard() {
  const { user, branding } = useAuth();
  const isHod = user.role === "HOD";
  const navigate = useNavigate();

  const [overview, setOverview] = useState(null);
  const [subs, setSubs] = useState([]);
  const [entries, setEntries] = useState([]);
  const [slots, setSlots] = useState([]);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);

  const today = new Date();
  const todayStr = today.toISOString().slice(0, 10);
  const todayDow = (today.getDay() + 6) % 7; // backend Mon=0

  useEffect(() => {
    let alive = true;
    async function load() {
      setLoading(true);
      try {
        const tasks = [api.substitutions(todayStr), api.activeTimetable(), api.timeSlots()];
        if (isHod) {
          tasks.push(api.overview(todayStr), api.activity(6));
        }
        const [sub, ent, sl, ov, act] = await Promise.all(tasks);
        if (!alive) return;
        setSubs(sub);
        setEntries(ent);
        setSlots(sl);
        if (isHod) {
          setOverview(ov);
          setActivity(act);
        }
      } finally {
        if (alive) setLoading(false);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, [isHod, todayStr]);

  const firstName = user.name.replace(/\(.*?\)/g, "").trim().split(/\s+/)[0];
  const dateLabel = today.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
  const dayName = today.toLocaleDateString("en-US", { weekday: "long" });

  const slotById = Object.fromEntries(slots.map((s) => [s.id, s]));
  const todaysClasses = entries
    .filter((e) => e.time_slot.day_of_week === todayDow)
    .sort((a, b) => a.time_slot.period_index - b.time_slot.period_index);
  const subEntryIds = new Set(subs.map((s) => s.id));

  return (
    <>
      {/* Welcome banner */}
      <section className="welcome-card">
        <div>
          <h2 className="welcome-title">
            {greeting()}, <span className="welcome-name">{firstName}</span>
          </h2>
          <p className="welcome-sub">Here's what's happening in your department today.</p>
        </div>
        <div className="welcome-date">
          <Icon path={icons.timetable} size={26} />
          <div>
            <div className="date-main">{dateLabel}</div>
            <div className="date-sub">{branding.semester_label}</div>
          </div>
        </div>
      </section>

      {/* Stat cards */}
      {isHod &&
        (loading || !overview ? (
          <SkeletonStats count={4} />
        ) : (
          <div className="stat-row-4">
            <StatCard tone="blue" icon="teachers" value={overview.total_teachers} label="Total teachers" to="/teachers" />
            <StatCard tone="green" icon="checkCircle" value={overview.present_today} label="Present today" />
            <StatCard tone="red" icon="minusCircle" value={overview.absent_today} label="Absent today" to="/leaves" />
            <StatCard tone="amber" icon="substitutions" value={overview.substitutions_today} label="Substitutions" to="/substitutions" />
          </div>
        ))}

      <div className="dash-grid">
        {/* Left / main column */}
        <div className="dash-col-main">
          <div className="card">
            <div className="card-head">
              <h2>Today's substitutions</h2>
              {isHod && <Link to="/substitutions" className="view-all">View all →</Link>}
            </div>
            {loading ? (
              <SkeletonRows rows={4} />
            ) : (
              <div className="scroll-x">
                <table>
                  <thead>
                    <tr>
                      <th>Period</th>
                      <th>Class</th>
                      <th>Subject</th>
                      <th>Original teacher</th>
                      <th>Substitute</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {subs.length === 0 && (
                      <EmptyRow cols={6} icon="substitutions" text="No substitutions scheduled for today." />
                    )}
                    {subs.map((s) => (
                      <tr key={s.id}>
                        <td>{s.period.split(" ")[0]}</td>
                        <td>{s.class_section}</td>
                        <td>{s.subject}</td>
                        <td>{s.absent_teacher}</td>
                        <td>{s.substitute_teacher || "—"}</td>
                        <td>
                          {s.status === "ASSIGNED" ? (
                            <span className="pill green">Assigned</span>
                          ) : (
                            <span className="pill red">Unassigned</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-head">
              <h2>Today's timetable</h2>
              <Link to="/timetable" className="view-all">View full timetable →</Link>
            </div>
            {loading ? (
              <SkeletonRows rows={4} />
            ) : (
              <div className="scroll-x">
                <table>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Class</th>
                      <th>Subject</th>
                      <th>Teacher</th>
                      <th>Room</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {todaysClasses.length === 0 && (
                      <EmptyRow cols={6} icon="timetable" text={`No classes scheduled for today (${dayName}).`} />
                    )}
                    {todaysClasses.map((e) => (
                      <tr key={e.id}>
                        <td>
                          {e.time_slot.start_time} - {e.time_slot.end_time}
                        </td>
                        <td>{e.class_section.name}</td>
                        <td>{e.subject.name}</td>
                        <td>{e.teacher.name}</td>
                        <td>{e.room.name}</td>
                        <td>
                          <span className="pill blue">Scheduled</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right / side column */}
        <div className="dash-col-side">
          {isHod && (
            <div className="card">
              <h2>Quick actions</h2>
              <div className="quick-grid">
                <QuickAction icon="calendarPlus" label="Create timetable" onClick={() => navigate("/my-timetable")} />
                <QuickAction icon="userPlus" label="Add teacher" onClick={() => navigate("/teachers")} />
                <QuickAction icon="subjects" label="Add subject" soon />
                <QuickAction icon="substitutions" label="Manage substitutions" onClick={() => navigate("/substitutions")} />
              </div>
            </div>
          )}

          {isHod && (
            <div className="card">
              <div className="card-head">
                <h2>Recent activity</h2>
              </div>
              {loading ? (
                <SkeletonRows rows={5} />
              ) : activity.length === 0 ? (
                <p className="sub">No recent activity.</p>
              ) : (
                <ul className="activity-feed">
                  {activity.map((a) => (
                    <li key={a.id}>
                      <span className={"act-dot " + dotTone(a.action)} />
                      <div>
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
            <div className="card">
              <h2>Your day</h2>
              <p className="sub">
                You have {todaysClasses.length} class{todaysClasses.length === 1 ? "" : "es"} scheduled today.
              </p>
              <Link to="/leaves"><button style={{ width: "100%" }}>Register a leave</button></Link>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function StatCard({ tone, icon, value, label, to }) {
  const body = (
    <>
      <span className="stat-icon" aria-hidden="true">
        <Icon path={icons[icon]} size={22} />
      </span>
      <div className="stat-body">
        <div className="num">{value}</div>
        <div className="lbl">{label}</div>
      </div>
    </>
  );
  return to ? (
    <Link to={to} className={"stat-tile " + tone}>
      {body}
    </Link>
  ) : (
    <div className={"stat-tile " + tone}>{body}</div>
  );
}

function QuickAction({ icon, label, onClick, soon }) {
  return (
    <button
      type="button"
      className={"quick-action" + (soon ? " soon" : "")}
      onClick={soon ? undefined : onClick}
      disabled={soon}
    >
      <span className="qa-icon" aria-hidden="true">
        <Icon path={icons[icon]} size={22} />
      </span>
      <span>{label}</span>
      {soon && <span className="soon-dot">Soon</span>}
    </button>
  );
}

function EmptyRow({ cols, icon, text }) {
  return (
    <tr className="empty-row">
      <td colSpan={cols}>
        <div className="empty-inline">
          <Icon path={icons[icon]} size={32} />
          <span>{text}</span>
        </div>
      </td>
    </tr>
  );
}

function dotTone(action) {
  if (action === "OVERRIDE" || action === "CANCEL") return "amber";
  if (action === "CREATE") return "green";
  if (action === "APPROVE" || action === "GENERATE") return "indigo";
  return "blue";
}
function humanAction(a) {
  const map = {
    GENERATE: "Timetable generated",
    APPROVE: "Timetable published",
    CREATE: `${a.entity[0].toUpperCase() + a.entity.slice(1)} created`,
    CANCEL: "Leave cancelled",
    OVERRIDE: "Substitution reassigned",
  };
  const base = map[a.action] || `${a.action} ${a.entity}`;
  return a.actor ? `${base} · ${a.actor}` : base;
}
