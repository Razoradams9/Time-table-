import { useEffect, useState } from "react";
import { api } from "../api";
import PageHeader from "../components/PageHeader.jsx";
import { SkeletonRows } from "../components/Skeleton.jsx";

export default function Substitutions() {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [subs, setSubs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [panel, setPanel] = useState(null); // { sub, candidates, suggestions }
  const [busy, setBusy] = useState(false);

  async function load(d) {
    setLoading(true);
    setSubs(await api.substitutions(d));
    setLoading(false);
  }
  useEffect(() => {
    load(date);
  }, [date]);

  async function openPanel(sub) {
    setBusy(true);
    try {
      const [candidates, suggestions] = await Promise.all([
        api.candidates(sub.id),
        api.suggestions(sub.id),
      ]);
      setPanel({ sub, candidates, suggestions });
    } catch (ex) {
      alert(ex.message);
    } finally {
      setBusy(false);
    }
  }

  async function assign(subId, teacherId) {
    setBusy(true);
    try {
      await api.assignSub(subId, teacherId);
      setPanel(null);
      await load(date);
    } catch (ex) {
      alert(ex.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        badge="Coverage engine"
        title="Substitutions"
        subtitle="Review, reassign, or resolve uncovered periods with AI suggestions."
      >
        <div style={{ minWidth: 180 }}>
          <label>Date</label>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
      </PageHeader>

      <div className="card">
        {loading ? (
          <SkeletonRows rows={5} />
        ) : subs.length === 0 ? (
          <p className="sub">No substitutions on this date.</p>
        ) : (
          <div className="scroll-x">
            <table>
              <thead>
                <tr>
                  <th>Period</th>
                  <th>Subject</th>
                  <th>Class</th>
                  <th>Absent</th>
                  <th>Substitute</th>
                  <th>Status</th>
                  <th>Source</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {subs.map((s) => (
                  <tr key={s.id}>
                    <td>{s.period}</td>
                    <td>{s.subject}</td>
                    <td>{s.class_section}</td>
                    <td>{s.absent_teacher}</td>
                    <td>{s.substitute_teacher || "—"}</td>
                    <td>
                      {s.status === "ASSIGNED" ? (
                        <span className="pill green">Covered</span>
                      ) : (
                        <span className="pill red">Uncovered</span>
                      )}
                    </td>
                    <td>
                      <span className="pill gray">{s.source}</span>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <button className="ghost small" onClick={() => openPanel(s)} disabled={busy}>
                        Manage
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {panel && (
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <h2>
              Manage: {panel.sub.subject} · {panel.sub.class_section} · {panel.sub.period}
            </h2>
            <button className="ghost small" onClick={() => setPanel(null)}>
              Close
            </button>
          </div>
          <div className="explain">{panel.sub.explanation}</div>

          <h3 style={{ marginTop: 18, marginBottom: 6, fontSize: 15 }}>Ranked candidates</h3>
          {panel.candidates.length === 0 ? (
            <p className="sub">No teacher is currently free for this period.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Teacher</th>
                  <th>Score</th>
                  <th>Reasoning</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {panel.candidates.map((c) => (
                  <tr key={c.teacher_id}>
                    <td>{c.name}</td>
                    <td>{c.score}</td>
                    <td style={{ fontSize: 12, color: "var(--muted)" }}>{c.reason}</td>
                    <td style={{ textAlign: "right" }}>
                      <button className="small" onClick={() => assign(panel.sub.id, c.teacher_id)} disabled={busy}>
                        Assign
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h3 style={{ marginTop: 18, marginBottom: 6, fontSize: 15 }}>AI suggestions</h3>
          {panel.suggestions.map((sg, i) => (
            <div key={i} className="note-item">
              <div className="t">
                <span className="pill amber" style={{ marginRight: 6 }}>
                  {sg.kind}
                </span>
                {sg.description}
              </div>
              <div className="b">{sg.explanation}</div>
              {sg.kind === "CANDIDATE" && sg.payload.substitute_teacher_id && (
                <button
                  className="small"
                  style={{ marginTop: 8 }}
                  onClick={() => assign(panel.sub.id, sg.payload.substitute_teacher_id)}
                  disabled={busy}
                >
                  Apply this
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
