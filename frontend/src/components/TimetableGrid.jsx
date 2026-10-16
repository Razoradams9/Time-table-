const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

// A fully data-driven weekly grid.
//   entries : TimetableEntryOut[]
//   slots   : TimeSlotOut[] (defines the day/period structure)
//   mode    : "class"  -> cells emphasize teacher (who teaches this stream)
//             "teacher"-> cells emphasize class (where the teacher goes)
//             "master" -> cells show teacher + class
export default function TimetableGrid({ entries, slots, mode = "master" }) {
  // Distinct days present, sorted.
  const days = [...new Set(slots.map((s) => s.day_of_week))].sort((a, b) => a - b);

  // Distinct period indices, sorted -> each becomes a row (P1..Pn).
  const periodIdxs = [...new Set(slots.map((s) => s.period_index))].sort((a, b) => a - b);
  const timeByPeriod = {};
  const preferredByPeriod = {};
  for (const s of slots) {
    timeByPeriod[s.period_index] = `${s.start_time}–${s.end_time}`;
    preferredByPeriod[s.period_index] = s.is_preferred;
  }

  // Map day_period -> entry.
  const cellMap = {};
  for (const e of entries) {
    cellMap[`${e.time_slot.day_of_week}_${e.time_slot.period_index}`] = e;
  }

  // Detect break gaps between consecutive period rows (non-adjacent indices).
  const isBreakAfter = (i) =>
    i < periodIdxs.length - 1 && periodIdxs[i + 1] - periodIdxs[i] > 1;

  return (
    <div className="scroll-x">
      <div className="grid-tt" style={{ gridTemplateColumns: `96px repeat(${days.length}, 1fr)` }}>
        <div className="tt-head">Period</div>
        {days.map((d) => (
          <div className="tt-head" key={d}>
            {DAY_NAMES[d]}
          </div>
        ))}

        {periodIdxs.map((p, i) => (
          <Row
            key={p}
            label={`P${i + 1}`}
            time={timeByPeriod[p]}
            days={days}
            cells={days.map((d) => cellMap[`${d}_${p}`])}
            preferred={preferredByPeriod[p]}
            mode={mode}
            breakAfter={isBreakAfter(i)}
          />
        ))}
      </div>
    </div>
  );
}

function Row({ label, time, days, cells, preferred, mode, breakAfter }) {
  return (
    <>
      <div className={"tt-time" + (breakAfter ? " break-after" : "")}>
        <span className="tt-pnum">{label}</span>
        <span className="tt-ptime">{time}</span>
      </div>
      {cells.map((e, idx) => {
        const cls =
          "tt-cell" +
          (e ? " filled" : "") +
          (e?.is_double ? " lab" : "") +
          (preferred ? " preferred" : "") +
          (breakAfter ? " break-after" : "");
        if (!e) return <div className={cls} key={idx} />;
        return (
          <div className={cls} key={idx}>
            <div className="subj">
              {e.subject.name}
              {e.is_double && <span className="lab-tag">LAB</span>}
            </div>
            {mode !== "class" && <div className="meta">{e.class_section.name}</div>}
            {mode !== "teacher" && (
              <div className="meta">
                {e.teacher.name}
                {e.co_teacher ? ` & ${e.co_teacher.name}` : ""}
              </div>
            )}
            <div className="meta room">{e.room.name}</div>
          </div>
        );
      })}
    </>
  );
}
