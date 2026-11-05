// Local-date helpers (never use toISOString: it shifts the day by timezone).

export function localISO(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function parseISO(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function addDays(iso, n) {
  const d = parseISO(iso);
  d.setDate(d.getDate() + n);
  return localISO(d);
}

// Monday..Saturday of the week containing `iso`.
export function weekBounds(iso) {
  const d = parseISO(iso);
  const mondayOffset = (d.getDay() + 6) % 7;
  const start = addDays(iso, -mondayOffset);
  return { start, end: addDays(start, 5) };
}
