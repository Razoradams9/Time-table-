"""Shared date/time helpers for workload, course and compensation features."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Iterator


def _to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def slot_minutes(slot) -> int:
    """Duration in minutes of a TimeSlot, parsed from its 'HH:MM' start/end."""
    return _to_minutes(slot.end_time) - _to_minutes(slot.start_time)


def week_bounds(d: date) -> tuple[date, date]:
    """(Monday, Saturday) of the week containing d."""
    monday = d - timedelta(days=d.weekday())
    return monday, monday + timedelta(days=5)


def iter_teaching_dates(start: date, end: date) -> Iterator[date]:
    """Yield every Mon-Sat date in [start, end]."""
    cur = start
    while cur <= end:
        if cur.weekday() <= 5:
            yield cur
        cur += timedelta(days=1)


def round_hours(minutes: float) -> float:
    return round(minutes / 60, 2)
