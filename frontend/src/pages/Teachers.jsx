import { useEffect, useState } from "react";
import { api } from "../api";
import PageHeader from "../components/PageHeader.jsx";
import { SkeletonRows } from "../components/Skeleton.jsx";

const EMPTY_FORM = { name: "", email: "", max_periods_per_day: 6 };

export default function Teachers() {
  const [teachers, setTeachers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [busy, setBusy] = useState(false);
  // Credential to show once after create/reset: { label, email, password }
  const [credential, setCredential] = useState(null);

  async function load() {
    try {
      const t = await api.teachers();
      setTeachers(t);
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function submitNew(e) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const created = await api.createTeacher({
        name: form.name.trim(),
        email: form.email.trim(),
        max_periods_per_day: Number(form.max_periods_per_day) || 6,
      });
      setCredential({
        label: `Account created for ${created.name}`,
        email: created.email,
        password: created.initial_password,
      });
      setForm(EMPTY_FORM);
      setShowForm(false);
      await load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(t) {
    setErr("");
    try {
      if (t.is_active) await api.deactivateTeacher(t.id);
      else await api.activateTeacher(t.id);
      await load();
    } catch (ex) {
      setErr(ex.message);
    }
  }

  async function resetPassword(t) {
    setErr("");
    try {
      const res = await api.resetTeacherPassword(t.id);
      setCredential({
        label: `New temporary password for ${t.name}`,
        email: res.email,
        password: res.new_password,
      });
    } catch (ex) {
      setErr(ex.message);
    }
  }

  return (
    <>
      <PageHeader
        badge="Faculty"
        title="Teachers"
        subtitle="Manage department accounts: add faculty, reset passwords, and control access."
      >
        <button onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "Add teacher"}
        </button>
      </PageHeader>

      {credential && (
        <div className="card" style={{ borderLeft: "4px solid #16a34a" }}>
          <strong>{credential.label}</strong>
          <p className="sub" style={{ marginTop: 4 }}>
            Share these credentials securely. The teacher must change the password on first
            login. This password is shown only once.
          </p>
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap", marginTop: 8 }}>
            <div>
              <div className="label">Email</div>
              <code>{credential.email}</code>
            </div>
            <div>
              <div className="label">Temporary password</div>
              <code>{credential.password}</code>
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <button className="ghost small" onClick={() => setCredential(null)}>
              Dismiss
            </button>
          </div>
        </div>
      )}

      {showForm && (
        <div className="card">
          <form onSubmit={submitNew}>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              <div style={{ flex: "1 1 200px" }}>
                <label>Full name</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Dr. Jane Doe"
                  required
                />
              </div>
              <div style={{ flex: "1 1 200px" }}>
                <label>Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="jane@college.edu"
                  required
                />
              </div>
              <div style={{ flex: "0 1 160px" }}>
                <label>Max periods / day</label>
                <input
                  type="number"
                  min="1"
                  max="8"
                  value={form.max_periods_per_day}
                  onChange={(e) => setForm({ ...form, max_periods_per_day: e.target.value })}
                />
              </div>
            </div>
            <p className="sub" style={{ marginTop: 8 }}>
              A temporary password is generated automatically and shown once after creation.
            </p>
            <button type="submit" disabled={busy} style={{ marginTop: 8 }}>
              {busy ? "Creating…" : "Create account"}
            </button>
          </form>
        </div>
      )}

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
                  <th>Actions</th>
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
                    <td>
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        <button className="ghost small" onClick={() => resetPassword(t)}>
                          Reset password
                        </button>
                        {t.role !== "HOD" && (
                          <button className="ghost small" onClick={() => toggleActive(t)}>
                            {t.is_active ? "Deactivate" : "Activate"}
                          </button>
                        )}
                      </div>
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
