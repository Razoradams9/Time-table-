const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const DAY_IDXS = [0, 1, 2, 3, 4, 5];

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

  // Map: day -> period -> list of entries (usually one; may be more in the
  // unfiltered HOD view where two teachers share a class slot).
  const cellMap = {};
  for (const e of entries) {
    const d = e.time_slot.day_of_week;
    const p = e.time_slot.period_index;
    const key = `${d}_${p}`;
    (cellMap[key] = cellMap[key] || []).push(e);
  }

  return (
    <div className="scroll-x">
      <div className="grid-tt grid-tt-6">
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
      {DAY_IDXS.map((d) => {
        const list = cellMap[`${d}_${p}`];
        if (!list || list.length === 0)
          return <div className={`tt-cell${preferred ? " preferred" : ""}`} key={d} />;
        return (
          <div className={`tt-cell filled${preferred ? " preferred" : ""}`} key={d}>
            {list.map((e, i) => (
              <div key={e.id} className={i > 0 ? "tt-stack" : undefined}>
                <div className="subj">{e.subject.name}</div>
                <div className="meta">{e.class_section.name}</div>
                <div className="meta">{e.room.name}</div>
                {showTeacher && <div className="meta">{e.teacher.name}</div>}
              </div>
            ))}
          </div>
        );
      })}
    </>
  );
}
