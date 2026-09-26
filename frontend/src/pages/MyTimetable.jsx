import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import TimetableGrid from "../components/TimetableGrid.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { SkeletonTimetable } from "../components/Skeleton.jsx";

export default function MyTimetable() {
  const { user } = useAuth();
  const isHod = user.role === "HOD";
  const [entries, setEntries] = useState([]);
  const [slots, setSlots] = useState([]);
  const [subs, setSubs] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [selectedTeacherId, setSelectedTeacherId] = useState("all");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [genMsg, setGenMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      const tasks = [api.activeTimetable(), api.timeSlots(), api.substitutions()];
      if (isHod) tasks.push(api.teachers());
      const [e, s, sub, t] = await Promise.all(tasks);
      setEntries(e);
      setSlots(s);
      setSubs(sub);
      if (isHod && t) setTeachers(t);
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  // For the HOD: default the selector to the first teacher who actually has
  // periods, so they land on a readable single-teacher grid rather than "all".
  useEffect(() => {
    if (isHod && selectedTeacherId === "all" && teachers.length && entries.length) {
      const withPeriods = teachers.find((t) =>
        entries.some((e) => e.teacher.id === t.id)
      );
      if (withPeriods) setSelectedTeacherId(withPeriods.id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isHod, teachers, entries]);

  async function generate() {
    setBusy(true);
    setGenMsg("");
    try {
      const r = await api.generate();
      if (r.success) {
        await api.approve(r.version);
        setGenMsg(`Generated & approved v${r.version} (${r.entries} periods).`);
        await load();
      } else {
        setGenMsg(`Could not generate: ${r.message} ${(r.conflicts || []).join("; ")}`);
      }
    } catch (ex) {
      setGenMsg(ex.message);
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <>
        <PageHeader
          badge={isHod ? "Admin view" : "Your schedule"}
          title={isHod ? "Master Timetable" : "My Weekly Timetable"}
          subtitle="Loading your schedule…"
        />
        <div className="card product-card">
          <SkeletonTimetable />
        </div>
      </>
    );
  }

  const mySubs = subs.filter((s) => s.substitute_teacher === user.name);
  const coveredForMe = subs.filter((s) => s.absent_teacher === user.name && s.substitute_teacher);

  // HOD can view one teacher's grid at a time (matches the per-teacher photos),
  // or "all" for the combined master view.
  const viewingAll = !isHod || selectedTeacherId === "all";
  const gridEntries =
    isHod && selectedTeacherId !== "all"
      ? entries.filter((e) => e.teacher.id === Number(selectedTeacherId))
      : entries;
  const selectedTeacher = teachers.find((t) => t.id === Number(selectedTeacherId));

  return (
    <>
      <PageHeader
        badge={isHod ? "Admin view" : "Your schedule"}
        title={isHod ? "Teacher Timetables" : "My Weekly Timetable"}
        subtitle={
          isHod
            ? viewingAll
              ? "Combined master view. Pick a teacher to see their individual timetable."
              : `Individual timetable for ${selectedTeacher ? selectedTeacher.name : "teacher"}.`
            : "Your fixed weekly schedule. Substitutions you cover appear below."
        }
      >
        {isHod && (
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <select
              value={selectedTeacherId}
              onChange={(e) => setSelectedTeacherId(e.target.value)}
              style={{ minWidth: 200 }}
            >
              <option value="all">All teachers (master)</option>
              {teachers.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
            {entries.length > 0 && (
              <button className="ghost" onClick={generate} disabled={busy}>
                {busy ? "Regenerating…" : "Regenerate"}
              </button>
            )}
          </div>
        )}
      </PageHeader>

      <div className="card product-card">
        {err && <div className="error">{err}</div>}
        {entries.length === 0 ? (
          <div className="empty-state">
            <p>No active timetable yet.</p>
            {isHod && (
              <button onClick={generate} disabled={busy}>
                {busy ? "Generating…" : "Generate & approve timetable"}
              </button>
            )}
          </div>
        ) : gridEntries.length === 0 ? (
          <div className="empty-state">
            <p>{selectedTeacher ? `${selectedTeacher.name} has no scheduled periods.` : "No periods."}</p>
          </div>
        ) : (
          <TimetableGrid entries={gridEntries} slots={slots} showTeacher={viewingAll} />
        )}
        {genMsg && <div className="explain" style={{ marginTop: 12 }}>{genMsg}</div>}
      </div>

      {!isHod && mySubs.length > 0 && (
        <div className="card">
          <h2>Substitutions you are covering</h2>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Period</th>
                <th>Subject</th>
                <th>Class</th>
                <th>Room</th>
                <th>For</th>
              </tr>
            </thead>
            <tbody>
              {mySubs.map((s) => (
                <tr key={s.id}>
                  <td>{s.override_date}</td>
                  <td>{s.period}</td>
                  <td>{s.subject}</td>
                  <td>{s.class_section}</td>
                  <td>{s.room}</td>
                  <td>{s.absent_teacher}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!isHod && coveredForMe.length > 0 && (
        <div className="card">
          <h2>Your periods covered by others</h2>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Period</th>
                <th>Subject</th>
                <th>Class</th>
                <th>Covered by</th>
              </tr>
            </thead>
            <tbody>
              {coveredForMe.map((s) => (
                <tr key={s.id}>
                  <td>{s.override_date}</td>
                  <td>{s.period}</td>
                  <td>{s.subject}</td>
                  <td>{s.class_section}</td>
                  <td>
                    <span className="pill blue">Covered by {s.substitute_teacher}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
