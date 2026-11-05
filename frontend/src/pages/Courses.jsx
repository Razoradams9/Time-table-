import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import PageHeader from "../components/PageHeader.jsx";
import { SkeletonRows } from "../components/Skeleton.jsx";

const DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function Courses() {
  const [teachers, setTeachers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [query, setQuery] = useState("");
  const [teacherId, setTeacherId] = useState("");

  useEffect(() => {
    let alive = true;
    api
      .courses()
      .then((d) => alive && setTeachers(d.teachers))
      .catch((ex) => alive && setErr(ex.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const q = query.trim().toLowerCase();
  const visible = useMemo(() => {
    return teachers
      .filter((t) => !teacherId || String(t.teacher_id) === teacherId)
      .map((t) => {
        if (!q) return t;
        const nameHit = t.name.toLowerCase().includes(q);
        const courses = nameHit
          ? t.courses
          : t.courses.filter((c) =>
              [c.subject, c.class_section, c.subject_code].some((s) => s.toLowerCase().includes(q))
            );
        return { ...t, courses };
      })
      .filter((t) => !q || t.courses.length > 0);
  }, [teachers, q, teacherId]);

  return (
    <div>
      <PageHeader
        badge="Directory"
        title="Courses"
        subtitle="Every teacher's courses, taken from the active timetable."
      />

      <div className="card courses-toolbar">
        <input
          type="search"
          placeholder="Search teacher, subject, class or code"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search courses"
        />
        <select
          value={teacherId}
          onChange={(e) => setTeacherId(e.target.value)}
          aria-label="Filter by teacher"
        >
          <option value="">All teachers</option>
          {teachers.map((t) => (
            <option key={t.teacher_id} value={String(t.teacher_id)}>
              {t.name}
            </option>
          ))}
        </select>
      </div>

      {err && <div className="error">{err}</div>}
      {loading ? (
        <div className="card">
          <SkeletonRows rows={5} />
        </div>
      ) : visible.length === 0 && !err ? (
        <div className="card">
          <p className="sub" style={{ margin: 0 }}>No courses match your search.</p>
        </div>
      ) : (
        <div className="courses-grid">
          {visible.map((t) => (
            <div className="card" key={t.teacher_id}>
              <div className="card-head">
                <h3 style={{ margin: 0 }}>{t.name}</h3>
              </div>
              <div className="course-chips" style={{ marginBottom: 10 }}>
                <span className="pill blue">{t.total_courses} courses</span>
                <span className="pill green">{t.total_hours_per_week} h/week</span>
                <span className="pill gray">{t.total_periods_per_week} periods</span>
              </div>
              {t.courses.length === 0 ? (
                <p className="sub" style={{ margin: 0 }}>No courses in the active timetable.</p>
              ) : (
                t.courses.map((c) => (
                  <div className="course-row" key={`${c.subject_id}_${c.class_section_id}`}>
                    <div className="course-title">
                      <strong>{c.subject}</strong>
                      {c.is_lab && <span className="lab-tag">LAB</span>}
                    </div>
                    <div className="sub">
                      {c.class_section} · {c.periods_per_week} periods/wk · {c.hours_per_week} h/wk
                    </div>
                    {c.co_teachers.length > 0 && (
                      <div className="sub">
                        {c.role_in_course === "LEAD"
                          ? `with ${c.co_teachers.join(", ")}`
                          : `co-teaching with ${c.lead_teacher}`}
                      </div>
                    )}
                    <div className="course-chips">
                      {c.schedule.map((s, i) => (
                        <span className="course-chip" key={i} title={`${s.start_time}–${s.end_time} · ${s.room}`}>
                          {DAY_SHORT[s.day_of_week]} {s.period_label}
                        </span>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
