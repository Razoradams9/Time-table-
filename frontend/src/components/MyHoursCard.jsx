import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import { localISO, weekBounds } from "../dateUtils";
import { SkeletonRows } from "./Skeleton.jsx";
import DayBars from "./DayBars.jsx";

export default function MyHoursCard() {
  const { user } = useAuth();
  const [row, setRow] = useState(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    const { start, end } = weekBounds(localISO(new Date()));
    api
      .workload(start, end, user.teacher_id)
      .then((d) => alive && setRow(d.rows[0] || null))
      .catch(() => alive && setFailed(true))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [user.teacher_id]);

  if (failed || (!loading && !row)) return null;

  return (
    <div className="card my-hours">
      <h2>My teaching hours</h2>
      {loading ? (
        <SkeletonRows rows={3} />
      ) : (
        <>
          <div className="mh-big">
            {row.scheduled_hours_per_week}
            <span> h / week</span>
          </div>
          <p className="sub">{row.scheduled_periods_per_week} periods scheduled</p>
          <div className="mh-stats">
            <div>
              <div className="mh-num">{row.net_hours_in_range}</div>
              <div className="mh-lbl">Net this week</div>
            </div>
            <div>
              <div className="mh-num">+{row.hours_substituted_for_others}</div>
              <div className="mh-lbl">Substituted</div>
            </div>
            <div>
              <div className="mh-num">−{row.hours_given_up}</div>
              <div className="mh-lbl">Given up</div>
            </div>
          </div>
          <DayBars daily={row.daily} />
          <div className="mh-daynames" aria-hidden="true">
            {row.daily.map((d) => (
              <span key={d.day_of_week}>{d.day_name[0]}</span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
