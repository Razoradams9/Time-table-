import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import PageHeader from "../components/PageHeader.jsx";
import TimetableGrid from "../components/TimetableGrid.jsx";
import { SkeletonTimetable } from "../components/Skeleton.jsx";

export default function TimetableViews() {
  const { user } = useAuth();
  const isHod = user.role === "HOD";

  const [mode, setMode] = useState("teacher"); // "teacher" | "stream"
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

  // Load the grid whenever the selection changes.
  useEffect(() => {
    if (loadingOpts) return;
    const id = mode === "teacher" ? teacherId : classId;
    if (!id) {
      setEntries([]);
      return;
    }
    let alive = true;
    setLoadingGrid(true);
    (async () => {
      try {
        const data =
          mode === "teacher" ? await api.teacherTimetable(id) : await api.classTimetable(id);
        if (alive) setEntries(data);
      } catch (ex) {
        if (alive) setErr(ex.message);
      } finally {
        if (alive) setLoadingGrid(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [mode, teacherId, classId, loadingOpts, reloadKey]);

  const current = useMemo(() => {
    if (mode === "teacher") return options.teachers.find((t) => t.id === teacherId);
    return options.classes.find((c) => c.id === classId);
  }, [mode, teacherId, classId, options]);

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
        </div>
        {isHod && (
          <button onClick={regenerate} disabled={regen.busy}>
            {regen.busy ? "Regenerating…" : "↻ Regenerate timetable"}
          </button>
        )}
      </PageHeader>
      {regen.msg && <div className="explain" style={{ marginBottom: 18 }}>{regen.msg}</div>}

      <div className="card">
        <div className="row" style={{ marginBottom: 18 }}>
          <div className="col" style={{ maxWidth: 340 }}>
            <label>{mode === "teacher" ? "Select teacher" : "Select stream / class"}</label>
            {mode === "teacher" ? (
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

          {mode === "teacher" && current && (
            <div className="load-readout">
              <span className="pill blue">{busy} periods / week</span>
              <span className="pill green">{free} free slots</span>
              <span className={"pill " + loadClass(busy, totalSlots)}>{loadLabel(busy, totalSlots)}</span>
            </div>
          )}
        </div>

        {err && <div className="error">{err}</div>}

        {loadingOpts || loadingGrid ? (
          <SkeletonTimetable periods={8} />
        ) : entries.length === 0 ? (
          <div className="empty-state">
            <p>No timetable yet for this selection.</p>
            {isHod && <p className="sub">Generate &amp; approve a timetable on the Dashboard first.</p>}
          </div>
        ) : (
          <TimetableGrid entries={entries} slots={slots} mode={mode === "stream" ? "class" : "teacher"} />
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
