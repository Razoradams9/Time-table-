import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import { localISO } from "../dateUtils";
import { SkeletonRows } from "../components/Skeleton.jsx";
import { Icon, icons } from "../components/Icons.jsx";
import MyHoursCard from "../components/MyHoursCard.jsx";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function fmtDate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

export default function TeacherDashboard() {
  const { user, branding } = useAuth();
  const navigate = useNavigate();
  const [entries, setEntries] = useState([]);
  const [slots, setSlots] = useState([]);
  const [subs, setSubs] = useState([]);
  const [comps, setComps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const today = new Date();
  const todayStr = localISO(today);
  const todayDow = (today.getDay() + 6) % 7; // backend Mon=0

  useEffect(() => {
    let alive = true;
    Promise.all([
      api.activeTimetable(),
      api.timeSlots(),
      api.substitutions(),
      api.compensations({ status: "PROPOSED,SCHEDULED" }),
    ])
      .then(([ent, sl, sb, cp]) => {
        if (!alive) return;
        setEntries(ent);
        setSlots(sl);
        setSubs(sb);
        setComps(cp);
      })
      .catch((e) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const firstName = user.name.replace(/\(.*?\)/g, "").trim().split(/\s+/)[0];
  const dateLabel = today.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  const slotById = Object.fromEntries(slots.map((s) => [s.id, s]));
  const assignedToday = subs.filter((s) => s.override_date === todayStr && s.status === "ASSIGNED");

  // One row per period today: my own classes, classes I'm covering, my make-ups.
  const rows = [];
  for (const e of entries.filter((x) => x.time_slot.day_of_week === todayDow)) {
    const cover = assignedToday.find((s) => s.timetable_entry_id === e.id && s.absent_teacher_id === user.teacher_id);
    rows.push({
      key: `e${e.id}`,
      order: e.time_slot.period_index,
      time: `${e.time_slot.start_time} - ${e.time_slot.end_time}`,
      cls: e.class_section.name,
      subject: e.subject.name,
      room: e.room.name,
      tag: cover ? { tone: "amber", text: `Covered by ${cover.substitute_teacher || "—"}` } : { tone: "blue", text: "Scheduled" },
    });
  }
  for (const s of assignedToday.filter((x) => x.substitute_teacher_id === user.teacher_id)) {
    const sl = slotById[s.time_slot_id];
    rows.push({
      key: `s${s.id}`,
      order: s.period_index,
      time: sl ? `${sl.start_time} - ${sl.end_time}` : s.period,
      cls: s.class_section,
      subject: s.subject,
      room: s.room,
      tag: { tone: "green", text: `Covering ${s.absent_teacher}` },
    });
  }
  for (const c of comps.filter((x) => x.proposed_date === todayStr && x.status === "SCHEDULED")) {
    rows.push({
      key: `c${c.id}`,
      order: (slotById[c.proposed_time_slot_id]?.period_index ?? 99),
      time: c.proposed_start_time && c.proposed_end_time ? `${c.proposed_start_time} - ${c.proposed_end_time}` : c.proposed_period,
      cls: c.class_section,
      subject: c.subject,
      room: c.room || "—",
      tag: { tone: "indigo", text: "Make-up" },
    });
  }
  rows.sort((a, b) => a.order - b.order);

  const covering = subs
    .filter((s) => s.substitute_teacher_id === user.teacher_id && s.override_date >= todayStr)
    .sort((a, b) => a.override_date.localeCompare(b.override_date) || a.period_index - b.period_index);

  return (
    <>
      <section className="welcome-card">
        <div>
          <h2 className="welcome-title">
            {greeting()}, <span className="welcome-name">{firstName}</span>
          </h2>
          <p className="welcome-sub">Here's your day at a glance.</p>
        </div>
        <div className="welcome-date">
          <Icon path={icons.timetable} size={26} />
          <div>
            <div className="date-main">{dateLabel}</div>
            <div className="date-sub">{branding.semester_label}</div>
          </div>
        </div>
      </section>

      {error && <p className="error" role="alert">{error}</p>}

      <div className="dash-grid">
        <div className="dash-col-main">
          <div className="card">
            <div className="card-head">
              <h2>Today's classes</h2>
              <Link to="/timetable" className="view-all">My timetable →</Link>
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
                      <th>Room</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.length === 0 && (
                      <tr className="empty-row">
                        <td colSpan={5}>
                          <div className="empty-inline">
                            <Icon path={icons.timetable} size={32} />
                            <span>No classes for you today.</span>
                          </div>
                        </td>
                      </tr>
                    )}
                    {rows.map((r) => (
                      <tr key={r.key}>
                        <td>{r.time}</td>
                        <td>{r.cls}</td>
                        <td>{r.subject}</td>
                        <td>{r.room}</td>
                        <td>
                          <span className={"pill " + r.tag.tone}>{r.tag.text}</span>
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
              <h2>Substitutions I'm covering</h2>
            </div>
            {loading ? (
              <SkeletonRows rows={3} />
            ) : (
              <div className="scroll-x">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Period</th>
                      <th>Class</th>
                      <th>Subject</th>
                      <th>For</th>
                    </tr>
                  </thead>
                  <tbody>
                    {covering.length === 0 && (
                      <tr className="empty-row">
                        <td colSpan={5}>
                          <div className="empty-inline">
                            <Icon path={icons.substitutions} size={32} />
                            <span>You are not covering any upcoming classes.</span>
                          </div>
                        </td>
                      </tr>
                    )}
                    {covering.map((s) => (
                      <tr key={s.id}>
                        <td>{fmtDate(s.override_date)}</td>
                        <td>{s.period}</td>
                        <td>{s.class_section}</td>
                        <td>{s.subject}</td>
                        <td>{s.absent_teacher}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-head">
              <h2>My make-up classes</h2>
              <Link to="/compensations" className="view-all">View all →</Link>
            </div>
            {loading ? (
              <SkeletonRows rows={3} />
            ) : (
              <div className="scroll-x">
                <table>
                  <thead>
                    <tr>
                      <th>Missed</th>
                      <th>Class</th>
                      <th>Subject</th>
                      <th>Make-up slot</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comps.length === 0 && (
                      <tr className="empty-row">
                        <td colSpan={5}>
                          <div className="empty-inline">
                            <Icon path={icons.checkCircle} size={32} />
                            <span>No make-up classes pending.</span>
                          </div>
                        </td>
                      </tr>
                    )}
                    {comps.map((c) => (
                      <tr key={c.id}>
                        <td>{fmtDate(c.missed_date)}</td>
                        <td>{c.class_section}</td>
                        <td>{c.subject}</td>
                        <td>{c.proposed_date ? `${fmtDate(c.proposed_date)} ${c.proposed_period || ""}` : "—"}</td>
                        <td>
                          <span className={"pill " + (c.status === "SCHEDULED" ? "green" : "amber")}>
                            {c.status === "SCHEDULED" ? "Scheduled" : "Proposed"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        <div className="dash-col-side">
          <MyHoursCard />
          <div className="card">
            <h2>Quick actions</h2>
            <div className="quick-grid">
              <button type="button" className="quick-action" onClick={() => navigate("/leaves")}>
                <span className="qa-icon" aria-hidden="true">
                  <Icon path={icons.calendarPlus} size={22} />
                </span>
                <span>Register leave</span>
              </button>
              <button type="button" className="quick-action" onClick={() => navigate("/timetable")}>
                <span className="qa-icon" aria-hidden="true">
                  <Icon path={icons.timetable} size={22} />
                </span>
                <span>View my timetable</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
