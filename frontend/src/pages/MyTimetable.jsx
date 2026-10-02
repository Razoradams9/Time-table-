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
  const [classes, setClasses] = useState([]);
  const [viewMode, setViewMode] = useState("stream"); // "stream" | "teacher"
  const [selectedTeacherId, setSelectedTeacherId] = useState("all");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [genMsg, setGenMsg] = useState("");
  const [busy, setBusy] = useState(false);
  // Rebalance preview state: when set we show the proposed version instead of
  // the active one, with Approve / Discard actions.
  const [preview, setPreview] = useState(null); // { version, entries: [...] }

  async function load() {
    setLoading(true);
    setErr("");
    try {
      const tasks = [api.activeTimetable(), api.timeSlots(), api.substitutions()];
      if (isHod) {
        tasks.push(api.teachers());
        tasks.push(api.classes());
      }
      const [e, s, sub, t, c] = await Promise.all(tasks);
      setEntries(e);
      setSlots(s);
      setSubs(sub);
      if (isHod && t) setTeachers(t);
      if (isHod && c) setClasses(c);
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

  // Rebuild the whole table into comfortable positions, keeping all real
  // assignments. Shows a preview; the active timetable is untouched until approve.
  async function rebalance() {
    setBusy(true);
    setGenMsg("");
    try {
      const r = await api.rebalance();
      if (r.success) {
        const previewEntries = await api.timetableVersion(r.version);
        setPreview({ version: r.version, entries: previewEntries });
        setGenMsg(r.message);
      } else {
        setGenMsg(`Could not rebalance: ${r.message} ${(r.conflicts || []).join("; ")}`);
      }
    } catch (ex) {
      setGenMsg(ex.message);
    } finally {
      setBusy(false);
    }
  }

  async function approvePreview() {
    if (!preview) return;
    setBusy(true);
    try {
      await api.approve(preview.version);
      setPreview(null);
      setGenMsg(`Approved v${preview.version} as the active timetable.`);
      await load();
    } catch (ex) {
      setGenMsg(ex.message);
    } finally {
      setBusy(false);
    }
  }

  async function discardPreview() {
    if (!preview) return;
    setBusy(true);
    try {
      await api.discardVersion(preview.version);
      setGenMsg(`Discarded preview v${preview.version}. Your timetable is unchanged.`);
      setPreview(null);
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

  // When previewing a rebalance, show the proposed version's entries instead of
  // the active ones.
  const sourceEntries = preview ? preview.entries : entries;

  // --- Stream (class-section) view: one clean grid per class, stacked. ---
  // Sort streams by semester (S1, S3, S5) then name so the page reads naturally.
  const semOf = (name) => {
    const m = /S(\d+)/.exec(name || "");
    return m ? Number(m[1]) : 99;
  };
  const sortedClasses = [...classes].sort(
    (a, b) => semOf(a.name) - semOf(b.name) || a.name.localeCompare(b.name)
  );
  // Only show streams that actually have periods in the current source.
  const streamsWithEntries = sortedClasses
    .map((c) => ({
      cls: c,
      entries: sourceEntries.filter((e) => e.class_section.id === c.id),
    }))
    .filter((g) => g.entries.length > 0);

  // --- Teacher view: one teacher's grid at a time. ---
  const teacherEntries =
    selectedTeacherId !== "all"
      ? sourceEntries.filter((e) => e.teacher.id === Number(selectedTeacherId))
      : sourceEntries;
  const selectedTeacher = teachers.find((t) => t.id === Number(selectedTeacherId));

  return (
    <>
      <PageHeader
        badge={isHod ? "Admin view" : "Your schedule"}
        title={isHod ? "Master Timetable" : "My Weekly Timetable"}
        subtitle={
          isHod
            ? viewMode === "stream"
              ? "Organised by stream — each class section's full week, one after another."
              : `Individual timetable for ${selectedTeacher ? selectedTeacher.name : "teacher"}.`
            : "Your fixed weekly schedule. Substitutions you cover appear below."
        }
      >
        {isHod && (
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            {/* View toggle: by stream (default) or by teacher */}
            <div className="seg">
              <button
                className={viewMode === "stream" ? "seg-on" : ""}
                onClick={() => setViewMode("stream")}
              >
                By stream
              </button>
              <button
                className={viewMode === "teacher" ? "seg-on" : ""}
                onClick={() => setViewMode("teacher")}
              >
                By teacher
              </button>
            </div>
            {viewMode === "teacher" && (
              <select
                value={selectedTeacherId}
                onChange={(e) => setSelectedTeacherId(e.target.value)}
                style={{ minWidth: 200 }}
              >
                <option value="all">All teachers (combined)</option>
                {teachers.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            )}
            {entries.length > 0 && !preview && (
              <button className="ghost" onClick={rebalance} disabled={busy}>
                {busy ? "Rebalancing…" : "Rebalance timetable"}
              </button>
            )}
          </div>
        )}
      </PageHeader>

      {preview && (
        <div className="card" style={{ borderLeft: "4px solid #f59e0b" }}>
          <strong>Preview: rebalanced timetable v{preview.version}</strong>
          <p className="sub" style={{ marginTop: 4 }}>
            This keeps every teacher's real classes but spreads them into more
            comfortable positions (fewer back-to-back periods). You're previewing
            it below. Your current timetable is unchanged until you approve.
          </p>
          <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
            <button onClick={approvePreview} disabled={busy}>
              {busy ? "Working…" : "Approve & make active"}
            </button>
            <button className="ghost" onClick={discardPreview} disabled={busy}>
              Discard
            </button>
          </div>
        </div>
      )}

      {err && (
        <div className="card">
          <div className="error">{err}</div>
        </div>
      )}

      {entries.length === 0 ? (
        <div className="card product-card">
          <div className="empty-state">
            <p>No active timetable yet.</p>
            {isHod && (
              <button onClick={generate} disabled={busy}>
                {busy ? "Generating…" : "Generate & approve timetable"}
              </button>
            )}
          </div>
        </div>
      ) : isHod && viewMode === "stream" ? (
        // ---- Stream view: one clean grid per class section, stacked ----
        <>
          {streamsWithEntries.length === 0 ? (
            <div className="card product-card">
              <div className="empty-state">
                <p>No class periods to show.</p>
              </div>
            </div>
          ) : (
            streamsWithEntries.map(({ cls, entries: ce }) => (
              <div className="card product-card" key={cls.id}>
                <h2 style={{ marginTop: 0 }}>{cls.name}</h2>
                <TimetableGrid
                  entries={ce}
                  slots={slots}
                  showTeacher={true}
                  showClass={false}
                />
              </div>
            ))
          )}
          {genMsg && (
            <div className="card">
              <div className="explain">{genMsg}</div>
            </div>
          )}
        </>
      ) : (
        // ---- Teacher view (HOD single teacher / combined) or a teacher's own ----
        <div className="card product-card">
          {isHod && viewMode === "teacher" && teacherEntries.length === 0 ? (
            <div className="empty-state">
              <p>
                {selectedTeacher
                  ? `${selectedTeacher.name} has no scheduled periods.`
                  : "No periods."}
              </p>
            </div>
          ) : (
            <TimetableGrid
              entries={isHod ? teacherEntries : sourceEntries}
              slots={slots}
              showTeacher={!isHod || selectedTeacherId === "all"}
            />
          )}
          {genMsg && <div className="explain" style={{ marginTop: 12 }}>{genMsg}</div>}
        </div>
      )}

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
