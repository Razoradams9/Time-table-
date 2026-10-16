import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { SkeletonRows } from "../components/Skeleton.jsx";

export default function Teachers() {
  const { user } = useAuth();
  const [teachers, setTeachers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", max_periods_per_day: 5 });
  const [busy, setBusy] = useState(false);
  // Shown once after create/reset so the HOD can hand the password over.
  const [credential, setCredential] = useState(null); // { name, email, temp_password }

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setTeachers(await api.listAccounts());
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function addTeacher(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const res = await api.createAccount({
        name: form.name,
        email: form.email,
        max_periods_per_day: Number(form.max_periods_per_day),
      });
      setCredential({ name: res.name, email: res.email, temp_password: res.temp_password, kind: "created" });
      setShowAdd(false);
      setForm({ name: "", email: "", max_periods_per_day: 5 });
      await load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  async function resetPw(t) {
    if (!confirm(`Reset ${t.name}'s password? They'll be forced to set a new one on next login.`)) return;
    try {
      const res = await api.resetPassword(t.id);
      setCredential({ name: t.name, email: t.email, temp_password: res.temp_password, kind: "reset" });
    } catch (ex) {
      alert(ex.message);
    }
  }

  async function toggleActive(t) {
    try {
      await api.updateAccount(t.id, { is_active: !t.is_active });
      await load();
    } catch (ex) {
      alert(ex.message);
    }
  }

  return (
    <>
      <PageHeader
        badge="Faculty"
        title="Teachers"
        subtitle="Manage accounts: add staff, reset passwords, enable or disable access."
      >
        <button onClick={() => { setShowAdd((v) => !v); setCredential(null); }}>
          {showAdd ? "Cancel" : "+ Add teacher"}
        </button>
      </PageHeader>

      {credential && (
        <div className="card" style={{ borderColor: "var(--color-indigo)" }}>
          <h3 style={{ marginTop: 0 }}>
            {credential.kind === "created" ? "Account created" : "Password reset"} — temporary password
          </h3>
          <p className="sub">
            Share this with <strong>{credential.name}</strong> ({credential.email}). They must change it on
            first login. This is shown only once.
          </p>
          <div className="cred-box">
            <code>{credential.temp_password}</code>
            <button
              className="ghost small"
              onClick={() => navigator.clipboard?.writeText(credential.temp_password)}
            >
              Copy
            </button>
          </div>
          <button className="ghost small" style={{ marginTop: 12 }} onClick={() => setCredential(null)}>
            Dismiss
          </button>
        </div>
      )}

      {showAdd && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Add a teacher</h3>
          <form onSubmit={addTeacher}>
            <div className="row">
              <div className="col">
                <label>Full name</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              </div>
              <div className="col">
                <label>Email</label>
                <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
              </div>
              <div style={{ maxWidth: 150 }}>
                <label>Max periods/day</label>
                <input type="number" min="1" max="8" value={form.max_periods_per_day}
                       onChange={(e) => setForm({ ...form, max_periods_per_day: e.target.value })} />
              </div>
            </div>
            {err && <div className="error">{err}</div>}
            <div style={{ marginTop: 14 }}>
              <button type="submit" disabled={busy}>{busy ? "Creating…" : "Create account"}</button>
            </div>
            <p className="sub" style={{ marginTop: 10 }}>
              A temporary password is generated — you'll see it once to hand over.
            </p>
          </form>
        </div>
      )}

      <div className="card">
        {err && !showAdd && <div className="error">{err}</div>}
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
                  <th>Max / day</th>
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
                        <span className="pill gray">Disabled</span>
                      )}
                      {t.must_change_password && (
                        <span className="pill amber" style={{ marginLeft: 6 }}>Pending set</span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        <button className="ghost small" onClick={() => resetPw(t)}>Reset pw</button>
                        {t.id !== user.teacher_id && (
                          <button
                            className={(t.is_active ? "danger" : "") + " small"}
                            onClick={() => toggleActive(t)}
                          >
                            {t.is_active ? "Disable" : "Enable"}
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
