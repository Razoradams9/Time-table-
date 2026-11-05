import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import PageHeader from "../components/PageHeader.jsx";
import TimetableGrid from "../components/TimetableGrid.jsx";
import { SkeletonTimetable } from "../components/Skeleton.jsx";

export default function TimetableViews() {
  const { user } = useAuth();
  const isHod = user.role === "HOD";

  const [mode, setMode] = useState("teacher"); // "teacher" | "stream" | "adjusted"
  const [options, setOptions] = useState({ teachers: [], classes: [] });
  const [teacherId, setTeacherId] = useState(null);
  const [classId, setClassId] = useState(null);
  const [slots, setSlots] = useState([]);
  const [entries, setEntries] = useState([]);
  const [loadingOpts, setLoadingOpts] = useState(true);
  const [loadingGrid, setLoadingGrid] = useState(false);
  const [err, setErr] = useState("");
  const [regen, setRegen] = useState({ busy: false, msg: "" });
  const [reloadKey, setReloadKey] = useState(0);

  // Adjusted view: pick a date, overlay that day's substitutions on the grid.
  const todayStr = new Date().toISOString().slice(0, 10);
  const [adjDate, setAdjDate] = useState(todayStr);
  const [adjSubject, setAdjSubject] = useState("teacher"); // adjusted grid viewed by teacher or class
  const [subs, setSubs] = useState([]);
  const [makeups, setMakeups] = useState([]); // make-up classes held on adjDate

  // In adjusted mode we reuse the teacher/class pickers depending on adjSubject.
  const effectiveMode = mode === "adjusted" ? adjSubject : mode;

  async function regenerate() {
    if (!confirm("Regenerate and publish a fresh balanced timetable? This replaces the current active one.")) return;
    setRegen({ busy: true, msg: "" });
    try {
      const r = await api.generate();
      if (!r.success) {
        setRegen({ busy: false, msg: `Could not generate: ${r.message} ${(r.conflicts || []).join("; ")}` });
        return;
      }
      await api.approve(r.version);
      setRegen({ busy: false, msg: `Published v${r.version} (${r.entries} periods).` });
      setReloadKey((k) => k + 1); // trigger grid reload
    } catch (ex) {
      setRegen({ busy: false, msg: ex.message });
    }
  }

  // Load pickers + slots once.
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [opt, sl] = await Promise.all([api.viewOptions(), api.timeSlots()]);
        if (!alive) return;
        setOptions(opt);
        setSlots(sl);
        // Default selection: a teacher (self if present) and the first class.
        const self = opt.teachers.find((t) => t.id === user.teacher_id);
        setTeacherId((self || opt.teachers[0])?.id ?? null);
        setClassId(opt.classes[0]?.id ?? null);
      } catch (ex) {
        if (alive) setErr(ex.message);
      } finally {
        if (alive) setLoadingOpts(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [user.teacher_id]);

  // Load the grid whenever the selection changes. In adjusted mode we also
  // load the chosen date's substitutions so the grid can overlay them.
  useEffect(() => {
    if (loadingOpts) return;
    const id = effectiveMode === "teacher" ? teacherId : classId;
    if (!id) {
      setEntries([]);
      return;
    }
    let alive = true;
    setLoadingGrid(true);
    (async () => {
      try {
        const gridP =
          effectiveMode === "teacher" ? api.teacherTimetable(id) : api.classTimetable(id);
        const subsP = mode === "adjusted" ? api.substitutions(adjDate) : Promise.resolve([]);
        const makeupP = mode === "adjusted" ? api.compensationCalendar(adjDate) : Promise.resolve([]);
        const [data, subData, makeupData] = await Promise.all([gridP, subsP, makeupP]);
        if (!alive) return;
        setEntries(data);
        setSubs(subData);
        setMakeups(makeupData);
      } catch (ex) {
        if (alive) setErr(ex.message);
      } finally {
        if (alive) setLoadingGrid(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [mode, adjSubject, adjDate, teacherId, classId, loadingOpts, reloadKey]);

  const current = useMemo(() => {
    if (effectiveMode === "teacher") return options.teachers.find((t) => t.id === teacherId);
    return options.classes.find((c) => c.id === classId);
  }, [effectiveMode, teacherId, classId, options]);

  // Build the substitution overlay for the adjusted view, scoped to the
  // teacher or class currently being viewed, keyed by `day_period_index`.
  const subsByCell = useMemo(() => {
    if (mode !== "adjusted") return null;
    const map = {};
    for (const s of subs) {
      if (s.status === "CANCELLED") continue;
      const relevant =
        adjSubject === "teacher"
          ? s.absent_teacher_id === teacherId || s.substitute_teacher_id === teacherId
          : s.class_section_id === classId;
      if (!relevant) continue;
      map[`${s.day_of_week}_${s.period_index}`] = s;
    }
    return map;
  }, [mode, subs, adjSubject, teacherId, classId]);

  const makeupsForView = useMemo(() => {
    if (mode !== "adjusted") return [];
    return makeups.filter((m) =>
      adjSubject === "teacher" ? m.teacher_id === teacherId : m.class_section_id === classId
    );
  }, [mode, makeups, adjSubject, teacherId, classId]);

  // In the adjusted TEACHER view, a substitute's picked-up periods aren't on
  // their own base grid. Synthesize entries for those so the covering teacher
  // sees the extra duty slotted into their week.
  const gridEntries = useMemo(() => {
    if (mode !== "adjusted") return entries;
    const have = new Set(entries.map((e) => `${e.time_slot.day_of_week}_${e.time_slot.period_index}`));
    const extra = [];
    for (const s of adjSubject === "teacher" ? subs : []) {
      if (s.status === "CANCELLED") continue;
      if (s.substitute_teacher_id !== teacherId) continue;
      const key = `${s.day_of_week}_${s.period_index}`;
      if (have.has(key)) continue; // real clash handled elsewhere; don't overwrite
      have.add(key);
      extra.push({
        id: `sub-${s.id}`,
        is_double: false,
        time_slot: { day_of_week: s.day_of_week, period_index: s.period_index },
        subject: { name: s.subject },
        class_section: { name: s.class_section },
        teacher: { name: s.absent_teacher }, // original; grid shows substitute via overlay
        co_teacher: null,
        room: { name: s.room },
      });
    }
    // Make-up classes on this date for the viewed teacher / class (read-only overlay).
    for (const m of makeupsForView) {
      m.period_indexes.forEach((pi, n) => {
        const key = `${m.day_of_week}_${pi}`;
        if (have.has(key)) return; // never overwrite an occupied cell
        have.add(key);
        extra.push({
          id: `mk-${m.id}-${n}`,
          is_makeup: true,
          makeup_status: m.status,
          is_double: m.periods === 2,
          time_slot: { day_of_week: m.day_of_week, period_index: pi },
          subject: { name: m.subject },
          class_section: { name: m.class_section },
          teacher: { name: m.teacher },
          co_teacher: null,
          room: { name: m.room || "Room TBD" },
        });
      });
    }
    return extra.length ? [...entries, ...extra] : entries;
  }, [mode, adjSubject, entries, subs, teacherId, makeupsForView]);

  const adjCount = subsByCell ? Object.keys(subsByCell).length : 0;
  const makeupCount = makeupsForView.reduce((n, m) => n + m.periods, 0);

  // Load summary: count periods + free slots for the "exhaustion" readout.
  const totalSlots = useMemo(
    () => new Set(slots.map((s) => `${s.day_of_week}_${s.period_index}`)).size,
    [slots]
  );
  const busy = entries.length;
  const free = Math.max(0, totalSlots - busy);

  return (
    <>
      <PageHeader
        badge="Schedules"
        title="Timetable"
        subtitle="Browse the schedule teacher-wise or stream-wise."
      >
        <div className="seg">
          <button
            className={"seg-btn" + (mode === "teacher" ? " active" : "")}
            onClick={() => setMode("teacher")}
          >
            Teacher-wise
          </button>
          <button
            className={"seg-btn" + (mode === "stream" ? " active" : "")}
            onClick={() => setMode("stream")}
          >
            Stream-wise
          </button>
          <button
            className={"seg-btn" + (mode === "adjusted" ? " active" : "")}
            onClick={() => setMode("adjusted")}
            title="Original timetable with the day's substitutions applied"
          >
            Adjusted
          </button>
        </div>
        {isHod && (
          <button onClick={regenerate} disabled={regen.busy}>
            {regen.busy ? "Regenerating…" : "↻ Regenerate timetable"}
          </button>
        )}
      </PageHeader>
      {regen.msg && <div className="explain" style={{ marginBottom: 18 }}>{regen.msg}</div>}

      <div className="card">
        {/* Adjusted-mode controls: date + whether to view by teacher or class */}
        {mode === "adjusted" && (
          <div className="row" style={{ marginBottom: 18 }}>
            <div className="col" style={{ maxWidth: 220 }}>
              <label>Date</label>
              <input type="date" value={adjDate} onChange={(e) => setAdjDate(e.target.value)} />
            </div>
            <div className="col" style={{ maxWidth: 260 }}>
              <label>View adjusted schedule by</label>
              <div className="seg">
                <button
                  className={"seg-btn" + (adjSubject === "teacher" ? " active" : "")}
                  onClick={() => setAdjSubject("teacher")}
                >
                  Teacher
                </button>
                <button
                  className={"seg-btn" + (adjSubject === "stream" ? " active" : "")}
                  onClick={() => setAdjSubject("stream")}
                >
                  Class
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="row" style={{ marginBottom: 18 }}>
          <div className="col" style={{ maxWidth: 340 }}>
            <label>{effectiveMode === "teacher" ? "Select teacher" : "Select stream / class"}</label>
            {effectiveMode === "teacher" ? (
              <select value={teacherId ?? ""} onChange={(e) => setTeacherId(Number(e.target.value))}>
                {options.teachers.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} {t.role === "HOD" ? "(HOD)" : ""}
                  </option>
                ))}
              </select>
            ) : (
              <select value={classId ?? ""} onChange={(e) => setClassId(Number(e.target.value))}>
                {options.classes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {effectiveMode === "teacher" && mode !== "adjusted" && current && (
            <div className="load-readout">
              <span className="pill blue">{busy} periods / week</span>
              <span className="pill green">{free} free slots</span>
              <span className={"pill " + loadClass(busy, totalSlots)}>{loadLabel(busy, totalSlots)}</span>
            </div>
          )}

          {mode === "adjusted" && (
            <div className="load-readout">
              {adjCount > 0 || makeupCount > 0 ? (
                <span className="pill amber">
                  {adjCount} substitution{adjCount === 1 ? "" : "s"}, {makeupCount} make-up
                  {makeupCount === 1 ? "" : "s"}
                </span>
              ) : (
                <span className="pill gray">No substitutions or make-ups on this day</span>
              )}
            </div>
          )}
        </div>

        {mode === "adjusted" && (
          <p className="sub" style={{ marginTop: -6, marginBottom: 16 }}>
            Showing the original timetable with {new Date(adjDate + "T00:00:00").toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })}
            's substitutions applied. Changed periods are highlighted; the original teacher is shown struck through.
          </p>
        )}

        {err && <div className="error">{err}</div>}

        {loadingOpts || loadingGrid ? (
          <SkeletonTimetable periods={8} />
        ) : entries.length === 0 ? (
          <div className="empty-state">
            <p>No timetable yet for this selection.</p>
            {isHod && <p className="sub">Generate &amp; approve a timetable on the Dashboard first.</p>}
          </div>
        ) : (
          <TimetableGrid
            entries={gridEntries}
            slots={slots}
            mode={effectiveMode === "stream" ? "class" : "teacher"}
            subsByCell={subsByCell}
            viewTeacherId={effectiveMode === "teacher" ? teacherId : null}
          />
        )}
      </div>
    </>
  );
}

function loadClass(busy, total) {
  const ratio = total ? busy / total : 0;
  if (ratio > 0.6) return "red";
  if (ratio > 0.4) return "amber";
  return "green";
}
function loadLabel(busy, total) {
  const ratio = total ? busy / total : 0;
  if (ratio > 0.6) return "Heavy load";
  if (ratio > 0.4) return "Balanced";
  return "Light load";
}
