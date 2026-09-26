import { useState } from "react";
import { api, getToken } from "../api";
import PageHeader from "../components/PageHeader.jsx";

function weekAgo() {
  const d = new Date();
  d.setDate(d.getDate() - 7);
  return d.toISOString().slice(0, 10);
}

export default function Fairness() {
  const [start, setStart] = useState(weekAgo());
  const [end, setEnd] = useState(new Date().toISOString().slice(0, 10));
  const [rows, setRows] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [err, setErr] = useState("");

  async function run() {
    setErr("");
    try {
      setRows(await api.fairness(start, end));
      setLoaded(true);
    } catch (ex) {
      setErr(ex.message);
    }
  }

  // Exports need the auth header, so fetch as blob then trigger download.
  async function download(kind) {
    try {
      const res = await fetch(`/api/dashboard/export/fairness.${kind}?start=${start}&end=${end}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok) throw new Error(`Export failed (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `fairness_${start}_${end}.${kind}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (ex) {
      alert(ex.message);
    }
  }

  const max = Math.max(1, ...rows.map((r) => r.substitutions_given));

  return (
    <>
      <PageHeader
        badge="Balance"
        title="Fairness report"
        subtitle="See how substitution load is distributed across teachers, and export it."
      />
      <div className="card">
      <div className="row">
        <div className="col">
          <label>From</label>
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </div>
        <div className="col">
          <label>To</label>
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </div>
        <div>
          <button onClick={run}>Run report</button>
        </div>
        {loaded && (
          <div style={{ display: "flex", gap: 8 }}>
            <button className="ghost" onClick={() => download("csv")}>
              Export CSV
            </button>
            <button className="ghost" onClick={() => download("pdf")}>
              Export PDF
            </button>
          </div>
        )}
      </div>
      {err && <div className="error">{err}</div>}

      {loaded && (
        <table style={{ marginTop: 16 }}>
          <thead>
            <tr>
              <th>Teacher</th>
              <th>Substitutions given</th>
              <th style={{ width: "40%" }}>Distribution</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.teacher_id}>
                <td>{r.name}</td>
                <td>{r.substitutions_given}</td>
                <td>
                  <div className="bar-track">
                    <div
                      className="bar-fill"
                      style={{
                        width: `${(r.substitutions_given / max) * 100}%`,
                        minWidth: r.substitutions_given ? 8 : 2,
                      }}
                    />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      </div>
    </>
  );
}
