// Shimmering skeleton placeholders for smooth loading states.

export function SkeletonRows({ rows = 4 }) {
  return (
    <div>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="skeleton skeleton-row"
          style={{ width: `${90 - i * 8}%` }}
        />
      ))}
    </div>
  );
}

export function SkeletonStats({ count = 3 }) {
  return (
    <div className="stat-row">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="stat" style={{ opacity: 0.7 }}>
          <div className="skeleton" style={{ height: 34, width: "40%", marginBottom: 10 }} />
          <div className="skeleton" style={{ height: 14, width: "70%" }} />
        </div>
      ))}
    </div>
  );
}

// A skeleton shaped like the weekly timetable grid.
export function SkeletonTimetable({ periods = 5 }) {
  const cells = [];
  for (let p = 0; p < periods; p++) {
    cells.push(<div key={`t${p}`} className="skeleton" style={{ height: 68, borderRadius: 8, opacity: 0.6 }} />);
    for (let d = 0; d < 5; d++) {
      cells.push(<div key={`${p}-${d}`} className="skeleton skeleton-block" />);
    }
  }
  return (
    <div className="scroll-x">
      <div className="skeleton-grid">
        <div className="skeleton" style={{ height: 24, opacity: 0.5 }} />
        {["Mon", "Tue", "Wed", "Thu", "Fri"].map((d) => (
          <div key={d} className="skeleton" style={{ height: 24, opacity: 0.5 }} />
        ))}
        {cells}
      </div>
    </div>
  );
}

export default SkeletonRows;
