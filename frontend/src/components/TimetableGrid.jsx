const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"];

// entries: array of TimetableEntryOut. showTeacher: include teacher name in cell.
export default function TimetableGrid({ entries, slots, showTeacher = false }) {
  // Build period rows from distinct period_index in slots.
  const periodIdxs = [...new Set(slots.map((s) => s.period_index))].sort((a, b) => a - b);
  const timeByPeriod = {};
  for (const s of slots) {
    timeByPeriod[s.period_index] = `${s.start_time}-${s.end_time}`;
  }

  // Which period indexes are "preferred" (e.g. morning slots) — butter accent.
  const preferredPeriods = new Set(
    slots.filter((s) => s.is_preferred).map((s) => s.period_index)
  );

  // Map: day -> period -> entry
  const cellMap = {};
  for (const e of entries) {
    const d = e.time_slot.day_of_week;
    const p = e.time_slot.period_index;
    cellMap[`${d}_${p}`] = e;
  }

  return (
    <div className="scroll-x">
      <div className="grid-tt">
        <div className="tt-head">Period</div>
        {DAYS.map((d) => (
          <div className="tt-head" key={d}>
            {d}
          </div>
        ))}
        {periodIdxs.map((p) => (
          <RowFragment
            key={p}
            p={p}
            time={timeByPeriod[p]}
            cellMap={cellMap}
            showTeacher={showTeacher}
            preferred={preferredPeriods.has(p)}
          />
        ))}
      </div>
    </div>
  );
}

function RowFragment({ p, time, cellMap, showTeacher, preferred }) {
  return (
    <>
      <div className="tt-time">
        P{p + 1}
        <br />
        {time}
      </div>
      {[0, 1, 2, 3, 4].map((d) => {
        const e = cellMap[`${d}_${p}`];
        if (!e) return <div className={`tt-cell${preferred ? " preferred" : ""}`} key={d} />;
        return (
          <div className={`tt-cell filled${preferred ? " preferred" : ""}`} key={d}>
            <div className="subj">{e.subject.name}</div>
            <div className="meta">{e.class_section.name}</div>
            <div className="meta">{e.room.name}</div>
            {showTeacher && <div className="meta">{e.teacher.name}</div>}
          </div>
        );
      })}
    </>
  );
}
