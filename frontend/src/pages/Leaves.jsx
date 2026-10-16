import { useEffect, useState } from "react";
import { api } from "../api";
import PageHeader from "../components/PageHeader.jsx";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function Leaves() {
  const [leaves, setLeaves] = useState([]);
  const [slots, setSlots] = useState([]);
  const [date, setDate] = useState("");
  const [scope, setScope] = useState("FULL_DAY");
  const [reason, setReason] = useState("");
  const [periodIds, setPeriodIds] = useState([]);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const [lv, s] = await Promise.all([api.myLeaves(), api.timeSlots()]);
    setLeaves(lv);
    setSlots(s);
  }
  useEffect(() => {
    load();
  }, []);

  // When a date is picked, the relevant slots are those on that weekday.
  const weekday = date ? new Date(date + "T00:00:00").getDay() : null;
  // JS: Sunday=0..Saturday=6; backend: Monday=0..Sunday=6
  const backendDow = weekday === null ? null : (weekday + 6) % 7;
  const daySlots = slots
    .filter((s) => s.day_of_week === backendDow)
    .sort((a, b) => a.period_index - b.period_index);

  function togglePeriod(id) {
    setPeriodIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function submit(e) {
    e.preventDefault();
    setErr("");
    setMsg("");
    setBusy(true);
    try {
      await api.createLeave({
        leave_date: date,
        scope,
        reason: reason || null,
        time_slot_ids: scope === "PERIODS" ? periodIds : [],
      });
      setMsg("Leave registered. Substitutes are being assigned automatically.");
      setDate("");
      setReason("");
      setScope("FULL_DAY");
      setPeriodIds([]);
      await load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  async function cancel(id) {
    if (!confirm("Cancel this leave? Related substitutions will be reverted.")) return;
    try {
      await api.cancelLeave(id);
      await load();
    } catch (ex) {
      alert(ex.message);
    }
  }

  const today = new Date().toISOString().slice(0, 10);

  return (
    <>
      <PageHeader
        badge="Time off"
        title="Leaves"
        subtitle="Register your absence and let the system arrange cover automatically."
      />
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Register a leave</h3>
        <p className="sub">Pick the day you'll be absent. The system finds substitutes for every affected period.</p>
        <form onSubmit={submit}>
          <div className="row">
            <div className="col">
              <label>Date</label>
              <input type="date" min={today} value={date} onChange={(e) => setDate(e.target.value)} required />
            </div>
            <div className="col">
              <label>Scope</label>
              <select value={scope} onChange={(e) => setScope(e.target.value)}>
                <option value="FULL_DAY">Full day</option>
                <option value="PERIODS">Specific periods</option>
              </select>
            </div>
            <div className="col">
              <label>Reason (optional)</label>
              <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. medical" />
            </div>
          </div>

          {scope === "PERIODS" && (
            <div style={{ marginTop: 12 }}>
              <label>Select periods {date ? `(${DAYS[weekday]})` : "(pick a date first)"}</label>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {daySlots.length === 0 && <span className="sub">No periods scheduled on this day.</span>}
                {daySlots.map((s) => (
                  <label
                    key={s.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      padding: "6px 10px",
                      cursor: "pointer",
                      background: periodIds.includes(s.id) ? "#eff6ff" : "#fff",
                    }}
                  >
                    <input
                      type="checkbox"
                      style={{ width: "auto" }}
                      checked={periodIds.includes(s.id)}
                      onChange={() => togglePeriod(s.id)}
                    />
                    P{s.period_index + 1} ({s.start_time})
                  </label>
                ))}
              </div>
            </div>
          )}

          {err && <div className="error">{err}</div>}
          {msg && <div className="explain" style={{ marginTop: 10 }}>{msg}</div>}
          <div style={{ marginTop: 14 }}>
            <button type="submit" disabled={busy}>
              {busy ? "Submitting…" : "Submit leave"}
            </button>
          </div>
        </form>
      </div>

      <div className="card">
        <h2>Leave history</h2>
        {leaves.length === 0 ? (
          <p className="sub">No leaves yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Scope</th>
                <th>Reason</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {leaves.map((lv) => {
                const upcoming = lv.leave_date >= today && lv.status === "ACTIVE";
                return (
                  <tr key={lv.id}>
                    <td>{lv.leave_date}</td>
                    <td>{lv.scope === "FULL_DAY" ? "Full day" : "Periods"}</td>
                    <td>{lv.reason || "—"}</td>
                    <td>
                      <span className={`pill ${lv.status === "ACTIVE" ? "green" : "gray"}`}>{lv.status}</span>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      {upcoming && (
                        <button className="danger small" onClick={() => cancel(lv.id)}>
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
