// Six tiny Mon-Sat bars; height is proportional to hours (shared scale via `max`).
export default function DayBars({ daily, max }) {
  const top = Math.max(max || 0, ...daily.map((d) => d.hours), 0.01);
  return (
    <div className="wl-days" role="img" aria-label={daily.map((d) => `${d.day_name} ${d.hours} hours`).join(", ")}>
      {daily.map((d) => (
        <span
          key={d.day_of_week}
          className="wl-day"
          title={`${d.day_name} ${d.hours} h`}
          style={{ height: `${Math.max(d.hours ? 8 : 2, (d.hours / top) * 100)}%` }}
        />
      ))}
    </div>
  );
}
