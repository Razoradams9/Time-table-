import { Fragment, useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { Icon, icons } from "../components/Icons.jsx";
import { SkeletonRows } from "../components/Skeleton.jsx";

const FILTERS = [
  { key: "", label: "All" },
  { key: "PROPOSED", label: "Waiting for a slot" },
  { key: "SCHEDULED", label: "Scheduled" },
  { key: "COMPLETED", label: "Completed" },
  { key: "CANCELLED", label: "Cancelled" },
];
const PILL = { PROPOSED: "amber", SCHEDULED: "blue", COMPLETED: "green", CANCELLED: "gray" };
const STATUS_LABEL = {
  PROPOSED: "Waiting for a slot",
  SCHEDULED: "Scheduled",
  COMPLETED: "Completed",
  CANCELLED: "Cancelled",
};

function fmtDate(iso) {
  if (!iso) return "";
  return new Date(iso + "T00:00:00").toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function Tile({ tone, icon, value, label }) {
  return (
    <div className={"stat-tile " + tone}>
      <span className="stat-icon" aria-hidden="true">
        <Icon path={icons[icon]} size={22} />
      </span>
      <div className="stat-body">
        <div className="num">{value}</div>
        <div className="lbl">{label}</div>
      </div>
    </div>
  );
}

export default function Compensations() {
  const { user } = useAuth();
  const isHod = user.role === "HOD";

  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState(null);
  const [teachers, setTeachers] = useState([]);
  const [teacherId, setTeacherId] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [rowErr, setRowErr] = useState({});
  const [openId, setOpenId] = useState(null);
  const [sugs, setSugs] = useState({ loading: false, list: [] });
  const [backfill, setBackfill] = useState({ busy: false, msg: "" });

  const load = useCallback(async () => {
    try {
      const [list, sum] = await Promise.all([
        api.compensations({ status, teacher_id: isHod ? teacherId : "" }),
        api.compensationSummary(isHod && teacherId ? Number(teacherId) : undefined),
      ]);
      setItems(list);
      setSummary(sum);
      setErr("");
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setLoading(false);
    }
  }, [status, teacherId, isHod]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  useEffect(() => {
    if (!isHod) return;
    api.teachers().then(setTeachers).catch(() => {});
  }, [isHod]);

  async function act(id, fn) {
    setBusyId(id);
    setRowErr((r) => ({ ...r, [id]: "" }));
    try {
      await fn();
      setOpenId(null);
      await load();
    } catch (ex) {
      setRowErr((r) => ({ ...r, [id]: ex.message }));
    } finally {
      setBusyId(null);
    }
  }

  async function togglePick(c) {
    if (openId === c.id) {
      setOpenId(null);
      return;
    }
    setOpenId(c.id);
    setSugs({ loading: true, list: [] });
    setRowErr((r) => ({ ...r, [c.id]: "" }));
    try {
      const list = await api.compensationSuggestions(c.id);
      setSugs({ loading: false, list });
    } catch (ex) {
      setSugs({ loading: false, list: [] });
      setRowErr((r) => ({ ...r, [c.id]: ex.message }));
    }
  }

  function choose(c, s) {
    return act(c.id, () =>
      api.rescheduleCompensation(c.id, {
        date: s.date,
        time_slot_id: s.time_slot_id,
        time_slot2_id: s.time_slot2_id,
        room_id: s.room_id,
      })
    );
  }

  async function runBackfill() {
    setBackfill({ busy: true, msg: "" });
    try {
      const r = await api.backfillCompensations();
      setBackfill({
        busy: false,
        msg: `Created ${r.created} record(s) covering ${r.periods} period(s); ${r.skipped} substitution(s) already tracked.`,
      });
      await load();
    } catch (ex) {
      setBackfill({ busy: false, msg: ex.message });
    }
  }

  const canAct = (c) => c.status === "PROPOSED" || c.status === "SCHEDULED";

  return (
    <div>
      <PageHeader
        badge="Syllabus"
        title="Compensations"
        subtitle="Make-up classes owed after a substitution, so no syllabus is lost."
      >
        {isHod && (
          <button className="ghost" onClick={runBackfill} disabled={backfill.busy}>
            {backfill.busy ? "Working…" : "Backfill existing"}
          </button>
        )}
      </PageHeader>
      {backfill.msg && <div className="explain" style={{ marginBottom: 18 }}>{backfill.msg}</div>}

      {summary && (
        <div className="stat-row-4" style={{ marginBottom: 18 }}>
          <Tile tone="blue" icon="substitutions" value={summary.owed} label="Periods owed" />
          <Tile tone="amber" icon="minusCircle" value={summary.proposed} label="Waiting for a slot" />
          <Tile tone="blue" icon="calendarPlus" value={summary.scheduled} label="Scheduled" />
          <Tile tone="green" icon="checkCircle" value={summary.completed} label="Completed" />
        </div>
      )}

      <div className="card">
        <div className="comp-toolbar">
          <div className="seg" role="group" aria-label="Filter by status">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                className={"seg-btn" + (status === f.key ? " active" : "")}
                onClick={() => setStatus(f.key)}
              >
                {f.label}
              </button>
            ))}
          </div>
          {isHod && (
            <select
              value={teacherId}
              onChange={(e) => setTeacherId(e.target.value)}
              aria-label="Filter by teacher"
            >
              <option value="">All teachers</option>
              {teachers.map((t) => (
                <option key={t.id} value={String(t.id)}>
                  {t.name}
                </option>
              ))}
            </select>
          )}
        </div>

        {err && <div className="error">{err}</div>}

        {loading ? (
          <SkeletonRows rows={5} />
        ) : items.length === 0 ? (
          <div className="empty-state">
            <p>No make-up classes{status ? " with this status" : ""}.</p>
            <p className="sub">They appear automatically when a teacher's period is substituted.</p>
          </div>
        ) : (
          <div className="scroll-x">
            <table className="comp-table">
              <thead>
                <tr>
                  <th>Teacher</th>
                  <th>Subject</th>
                  <th>Class</th>
                  <th>Missed on</th>
                  <th>Make-up</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((c) => (
                  <Fragment key={c.id}>
                    <tr>
                      <td>{c.teacher}</td>
                      <td>
                        {c.subject}
                        {c.periods === 2 && <span className="lab-tag">2 PERIODS</span>}
                        {c.is_lab && c.periods === 1 && <span className="lab-tag">LAB</span>}
                      </td>
                      <td>{c.class_section}</td>
                      <td>
                        {fmtDate(c.missed_date)}
                        <div className="sub">{c.missed_period}</div>
                      </td>
                      <td>
                        {c.proposed_date ? (
                          <>
                            {fmtDate(c.proposed_date)}
                            <div className="sub">
                              {c.proposed_period}
                              {c.room ? ` · ${c.room}` : ""}
                            </div>
                          </>
                        ) : (
                          <span className="sub">{c.status === "CANCELLED" ? "—" : "No slot found"}</span>
                        )}
                      </td>
                      <td>
                        <span className={"pill " + PILL[c.status]}>{STATUS_LABEL[c.status]}</span>
                      </td>
                      <td>
                        <div className="comp-actions">
                          {c.status === "PROPOSED" && c.proposed_date && (
                            <button
                              className="small"
                              disabled={busyId === c.id}
                              onClick={() => act(c.id, () => api.confirmCompensation(c.id))}
                            >
                              Confirm
                            </button>
                          )}
                          {canAct(c) && (
                            <button
                              className="small ghost"
                              disabled={busyId === c.id}
                              onClick={() => togglePick(c)}
                              aria-expanded={openId === c.id}
                            >
                              Pick another slot
                            </button>
                          )}
                          {c.can_complete && (
                            <button
                              className="small"
                              disabled={busyId === c.id}
                              onClick={() => act(c.id, () => api.completeCompensation(c.id))}
                            >
                              Mark done
                            </button>
                          )}
                          {isHod && canAct(c) && (
                            <button
                              className="small danger"
                              disabled={busyId === c.id}
                              onClick={() => {
                                if (confirm("Cancel this make-up class? The teacher will be notified.")) {
                                  act(c.id, () => api.cancelCompensation(c.id));
                                }
                              }}
                            >
                              Cancel
                            </button>
                          )}
                        </div>
                        {rowErr[c.id] && <div className="error comp-err">{rowErr[c.id]}</div>}
                      </td>
                    </tr>
                    {openId === c.id && (
                      <tr className="comp-sub-row">
                        <td colSpan={7}>
                          {sugs.loading ? (
                            <SkeletonRows rows={2} />
                          ) : sugs.list.length === 0 ? (
                            <p className="sub" style={{ margin: 0 }}>
                              No free slot found in the next 3 weeks.
                            </p>
                          ) : (
                            <ul className="comp-sugs">
                              {sugs.list.map((s) => (
                                <li key={`${s.date}_${s.time_slot_id}`}>
                                  <div>
                                    <strong>{fmtDate(s.date)}</strong> · {s.period_label} · {s.room}
                                    <div className="sub">{s.reason}</div>
                                  </div>
                                  <button
                                    className="small"
                                    disabled={busyId === c.id}
                                    onClick={() => choose(c, s)}
                                  >
                                    Choose
                                  </button>
                                </li>
                              ))}
                            </ul>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
