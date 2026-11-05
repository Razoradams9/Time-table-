import { useEffect, useState } from "react";
import { api } from "../api";
import { localISO, weekBounds, addDays } from "../dateUtils";
import { SkeletonRows } from "./Skeleton.jsx";
import DayBars from "./DayBars.jsx";

const r2 = (n) => Math.round(n * 100) / 100;

export default function WorkloadPanel() {
  const initial = weekBounds(localISO(new Date()));
  const [start, setStart] = useState(initial.start);
  const [end, setEnd] = useState(initial.end);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setErr("");
    api
      .workload(start, end)
      .then((d) => alive && setData(d))
      .catch((ex) => alive && setErr(ex.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [start, end]);

  function shift(n) {
    setStart(addDays(start, n * 7));
    setEnd(addDays(end, n * 7));
  }
  function thisWeek() {
    const b = weekBounds(localISO(new Date()));
    setStart(b.start);
    setEnd(b.end);
  }

  const rows = data?.rows || [];
  const maxNet = Math.max(1, ...rows.map((r) => r.net_hours_in_range));
  const maxDay = Math.max(0.01, ...rows.flatMap((r) => r.daily.map((d) => d.hours)));
  const sum = (k) => r2(rows.reduce((a, r) => a + r[k], 0));

  return (
    <div className="card">
      <div className="wl-controls">
        <div className="col">
          <label>From</label>
          <input type="date" value={start} onChange={(e) => e.target.value && setStart(e.target.value)} />
        </div>
        <div className="col">
          <label>To</label>
          <input type="date" value={end} onChange={(e) => e.target.value && setEnd(e.target.value)} />
        </div>
        <div className="wl-nav">
          <button className="ghost" onClick={() => shift(-1)}>&lt; Prev week</button>
          <button className="ghost" onClick={thisWeek}>This week</button>
          <button className="ghost" onClick={() => shift(1)}>Next week &gt;</button>
        </div>
      </div>
      {err && <div className="error">{err}</div>}
      {loading ? (
        <SkeletonRows rows={6} />
      ) : (
        data && (
          <>
            <div className="scroll-x">
              <table className="wl-table">
                <thead>
                  <tr>
                    <th>Teacher</th>
                    <th>Scheduled h/wk</th>
                    <th>Substituted h</th>
                    <th>Given up h</th>
                    <th>Net h</th>
                    <th style={{ width: "22%" }}>Net load</th>
                    <th>Mon–Sat</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.teacher_id}>
                      <td>{r.name}</td>
                      <td title={`${r.scheduled_periods_per_week} periods/week`}>
                        {r.scheduled_hours_per_week}
                        <span className="wl-sub"> · {r.scheduled_periods_per_week} periods</span>
                      </td>
                      <td title={`${r.periods_substituted_for_others} periods`}>{r.hours_substituted_for_others}</td>
                      <td title={`${r.periods_given_up} periods`}>
                        {r.hours_given_up}
                        {r.uncovered_hours > 0 && <span className="wl-sub"> (+{r.uncovered_hours} uncovered)</span>}
                      </td>
                      <td><strong>{r.net_hours_in_range}</strong></td>
                      <td>
                        <div className="bar-track">
                          <div
                            className="bar-fill"
                            style={{ width: `${(r.net_hours_in_range / maxNet) * 100}%`, minWidth: r.net_hours_in_range ? 8 : 2 }}
                          />
                        </div>
                      </td>
                      <td><DayBars daily={r.daily} max={maxDay} /></td>
                    </tr>
                  ))}
                  <tr className="wl-total">
                    <td>Total</td>
                    <td>{sum("scheduled_hours_per_week")}</td>
                    <td>{sum("hours_substituted_for_others")}</td>
                    <td>{sum("hours_given_up")}</td>
                    <td>{sum("net_hours_in_range")}</td>
                    <td colSpan={2} />
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="wl-help">
              {data.teaching_days} teaching day{data.teaching_days === 1 ? "" : "s"} in range. {data.formula}.
              Substituted, given-up and net hours cover the selected dates only.
            </p>
          </>
        )
      )}
    </div>
  );
}
