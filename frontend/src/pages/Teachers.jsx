import { useEffect, useState } from "react";
import { api } from "../api";
import PageHeader from "../components/PageHeader.jsx";
import { SkeletonRows } from "../components/Skeleton.jsx";

export default function Teachers() {
  const [teachers, setTeachers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const t = await api.teachers();
        if (alive) setTeachers(t);
      } catch (ex) {
        if (alive) setErr(ex.message);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  return (
    <>
      <PageHeader
        badge="Faculty"
        title="Teachers"
        subtitle="Everyone in the department, their role, and daily teaching limit."
      />
      <div className="card">
        {err && <div className="error">{err}</div>}
        {loading ? (
          <SkeletonRows rows={6} />
        ) : (
          <div className="scroll-x">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Max periods / day</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {teachers.map((t) => (
                  <tr key={t.id}>
                    <td style={{ fontWeight: 600 }}>{t.name}</td>
                    <td>{t.email}</td>
                    <td>
                      <span className={"pill " + (t.role === "HOD" ? "indigo" : "blue")}>
                        {t.role === "HOD" ? "HOD / Admin" : "Teacher"}
                      </span>
                    </td>
                    <td>{t.max_periods_per_day}</td>
                    <td>
                      {t.is_active ? (
                        <span className="pill green">Active</span>
                      ) : (
                        <span className="pill gray">Inactive</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
