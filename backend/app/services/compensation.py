"""Compensation (make-up class) engine.

When a teacher is absent and a period is covered (ASSIGNED) or left UNCOVERED,
the ABSENT teacher owes a make-up class for the same subject and class. One
record is created per substituted period; a lab block (two consecutive
is_double halves) becomes one `periods=2` record when a consecutive pair can be
found, otherwise two single records.

Scheduling rules (all enforced by `_check_*`, shared by suggestions and by
manual confirm/reschedule validation):
  - date is after the missed date, today or later, Monday-Saturday
  - teacher is active and has no ACTIVE leave on that date (any scope)
  - slots lie inside the class time window (MORNING / AFTERNOON / ANY)
  - a 2-period (lab) record needs two slots on one day with period_index diff 1
  - teacher is free: base entries (teacher or co-teacher), ASSIGNED
    substitutions as substitute, and other PROPOSED/SCHEDULED make-ups
  - declared Availability is respected
  - teacher day load incl. the candidate <= max_periods_per_day
  - longest run of consecutive ordinal slots <= settings.max_consecutive_periods
  - class is free (base entries and other make-ups)
  - room is free at every slot and room.is_lab matches the record

Suggestions search the week of max(missed_date, today) plus the next two weeks
and rank by (week offset, date, teacher load that day, adjacency, period).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, object_session

from app.config import settings
from app.models import (
    Availability,
    ClassSection,
    Compensation,
    CompensationStatus,
    Leave,
    LeaveStatus,
    Role,
    Room,
    Substitution,
    SubstitutionStatus,
    Teacher,
    TimeSlot,
    TimetableEntry,
)
from app.schemas import CompensationOut
from app.services import audit
from app.services.notifications import notify
from app.services.schedule_utils import week_bounds
from app.services.timetable_generator import _window_slot_ids

logger = logging.getLogger("compensation")

ACTIVE_STATUSES = (CompensationStatus.PROPOSED, CompensationStatus.SCHEDULED)
NO_SLOT_NOTE = "No free slot found in the next 3 weeks"
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
HORIZON_WEEKS = 3


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --------------------------------------------------------------------------
# Environment (cached lookups for one scheduling pass)
# --------------------------------------------------------------------------
@dataclass
class _Day:
    teacher_busy: dict[int, set[int]]
    class_busy: dict[int, set[int]]
    room_busy: dict[int, set[int]]
    on_leave: set[int]


@dataclass
class Suggestion:
    date: date
    day_name: str
    time_slot_id: int
    time_slot2_id: int | None
    period_label: str
    start_time: str
    end_time: str
    room_id: int
    room: str
    week_offset: int
    teacher_load_that_day: int
    reason: str


class _Env:
    def __init__(self, db: Session, exclude_comp_id: int | None = None) -> None:
        self.db = db
        self.exclude = exclude_comp_id
        self.slots: list[TimeSlot] = list(db.scalars(select(TimeSlot)).all())
        self.slot_by_id = {s.id: s for s in self.slots}
        self.slots_by_day: dict[int, list[TimeSlot]] = {}
        for s in self.slots:
            self.slots_by_day.setdefault(s.day_of_week, []).append(s)
        for lst in self.slots_by_day.values():
            lst.sort(key=lambda s: s.period_index)
        self.ordinal: dict[int, int] = {}
        for lst in self.slots_by_day.values():
            for i, s in enumerate(lst):
                self.ordinal[s.id] = i
        self.morning, self.afternoon = _window_slot_ids(list(self.slots))
        declared: dict[int, set[int]] = {}
        for a in db.scalars(select(Availability)).all():
            declared.setdefault(a.teacher_id, set()).add(a.time_slot_id)
        self.avail = declared  # absent key = unrestricted
        self.rooms: list[Room] = list(db.scalars(select(Room).order_by(Room.id)).all())
        self.room_by_id = {r.id: r for r in self.rooms}
        self._days: dict[date, _Day] = {}

    def window_ids(self, class_id: int) -> set[int] | None:
        cs = self.db.get(ClassSection, class_id)
        tw = (cs.time_window if cs else "ANY") or "ANY"
        if tw == "MORNING":
            return self.morning
        if tw == "AFTERNOON":
            return self.afternoon
        return None

    def day(self, d: date) -> _Day:
        cached = self._days.get(d)
        if cached is not None:
            return cached
        db = self.db
        t_busy: dict[int, set[int]] = {}
        c_busy: dict[int, set[int]] = {}
        r_busy: dict[int, set[int]] = {}
        entries = db.scalars(
            select(TimetableEntry)
            .join(TimeSlot, TimetableEntry.time_slot_id == TimeSlot.id)
            .where(TimetableEntry.is_active.is_(True), TimeSlot.day_of_week == d.weekday())
        ).all()
        for e in entries:
            t_busy.setdefault(e.teacher_id, set()).add(e.time_slot_id)
            if e.co_teacher_id:
                t_busy.setdefault(e.co_teacher_id, set()).add(e.time_slot_id)
            c_busy.setdefault(e.class_section_id, set()).add(e.time_slot_id)
            r_busy.setdefault(e.room_id, set()).add(e.time_slot_id)
        sub_rows = db.execute(
            select(Substitution.substitute_teacher_id, TimetableEntry.time_slot_id)
            .join(TimetableEntry, Substitution.timetable_entry_id == TimetableEntry.id)
            .where(
                Substitution.override_date == d,
                Substitution.status == SubstitutionStatus.ASSIGNED,
                Substitution.substitute_teacher_id.is_not(None),
            )
        ).all()
        for tid, sid in sub_rows:
            t_busy.setdefault(tid, set()).add(sid)
        stmt = select(Compensation).where(
            Compensation.proposed_date == d, Compensation.status.in_(ACTIVE_STATUSES)
        )
        if self.exclude is not None:
            stmt = stmt.where(Compensation.id != self.exclude)
        for c in db.scalars(stmt).all():
            for sid in (c.proposed_time_slot_id, c.proposed_time_slot2_id):
                if sid is None:
                    continue
                t_busy.setdefault(c.teacher_id, set()).add(sid)
                c_busy.setdefault(c.class_section_id, set()).add(sid)
                if c.room_id:
                    r_busy.setdefault(c.room_id, set()).add(sid)
        on_leave = set(
            db.scalars(
                select(Leave.teacher_id).where(Leave.leave_date == d, Leave.status == LeaveStatus.ACTIVE)
            ).all()
        )
        result = _Day(t_busy, c_busy, r_busy, on_leave)
        self._days[d] = result
        return result


def _longest_run(ords: set[int]) -> int:
    best = run = 0
    prev = None
    for o in sorted(ords):
        run = run + 1 if prev is not None and o == prev + 1 else 1
        best = max(best, run)
        prev = o
    return best


def _preferred_room_id(db: Session, comp: Compensation) -> int | None:
    if comp.substitution_id:
        sub = db.get(Substitution, comp.substitution_id)
        if sub is not None and sub.timetable_entry is not None:
            return sub.timetable_entry.room_id
    return None


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------
def _check_date(comp: Compensation, d: date) -> str | None:
    if d <= comp.missed_date:
        return f"The make-up must be after the missed class ({comp.missed_date})."
    if d < date.today():
        return "The make-up date cannot be in the past."
    if d.weekday() > 5:
        return "There are no classes on Sunday."
    return None


def _check_core(env: _Env, comp: Compensation, d: date, slot_ids: list[int]) -> str | None:
    """Date, teacher and class checks (everything except the room)."""
    reason = _check_date(comp, d)
    if reason:
        return reason
    teacher = env.db.get(Teacher, comp.teacher_id)
    if teacher is None or not teacher.is_active:
        return "The teacher is not active."
    day = env.day(d)
    if comp.teacher_id in day.on_leave:
        return f"{teacher.name} is on leave on {d}."

    window = env.window_ids(comp.class_section_id)
    if window is not None and any(s not in window for s in slot_ids):
        cs = env.db.get(ClassSection, comp.class_section_id)
        return f"Outside the {cs.time_window.lower()} time window of {cs.name}."

    busy = day.teacher_busy.get(comp.teacher_id, set())
    if any(s in busy for s in slot_ids):
        return f"{teacher.name} already has a class in that period."
    declared = env.avail.get(comp.teacher_id)
    if declared is not None and any(s not in declared for s in slot_ids):
        return f"{teacher.name} has not marked that period as available."
    if len(busy) + len(slot_ids) > teacher.max_periods_per_day:
        return f"{teacher.name} would exceed {teacher.max_periods_per_day} periods that day."
    ords = {env.ordinal[s] for s in busy | set(slot_ids)}
    if _longest_run(ords) > settings.max_consecutive_periods:
        return f"{teacher.name} would have more than {settings.max_consecutive_periods} periods in a row."

    cbusy = day.class_busy.get(comp.class_section_id, set())
    if any(s in cbusy for s in slot_ids):
        cs = env.db.get(ClassSection, comp.class_section_id)
        return f"{cs.name} already has a class in that period."
    return None


def _free_rooms(env: _Env, comp: Compensation, d: date, slot_ids: list[int]) -> list[int]:
    """Room ids free at every slot with the right type, preferred room first."""
    day = env.day(d)
    free = [
        r.id
        for r in env.rooms
        if r.is_lab == comp.is_lab and not any(s in day.room_busy.get(r.id, set()) for s in slot_ids)
    ]
    pref = _preferred_room_id(env.db, comp)
    if pref in free:
        free.remove(pref)
        free.insert(0, pref)
    return free


def _ordinal_map(slots: list[TimeSlot]) -> dict[int, int]:
    return {p: i for i, p in enumerate(sorted({s.period_index for s in slots}))}


def _label_for(slots: list[TimeSlot], ordinals: dict[int, int]) -> str:
    slots = sorted(slots, key=lambda s: s.period_index)
    first, last = slots[0], slots[-1]
    if len(slots) == 1:
        return f"P{ordinals[first.period_index] + 1} {first.start_time}-{first.end_time}"
    return (
        f"P{ordinals[first.period_index] + 1}-P{ordinals[last.period_index] + 1} "
        f"{first.start_time}-{last.end_time}"
    )


def _candidate_groups(env: _Env, comp: Compensation, dow: int) -> list[list[int]]:
    slots = env.slots_by_day.get(dow, [])
    if comp.periods == 2:
        return [
            [a.id, b.id]
            for a, b in zip(slots, slots[1:])
            if b.period_index - a.period_index == 1
        ]
    return [[s.id] for s in slots]


# --------------------------------------------------------------------------
# Suggestions / validation
# --------------------------------------------------------------------------
def suggest_slots(db: Session, comp: Compensation, limit: int = 12) -> list[Suggestion]:
    env = _Env(db, comp.id)
    ordinals = _ordinal_map(env.slots)
    today = date.today()
    anchor = week_bounds(max(comp.missed_date, today))[0]
    ranked: list[tuple[tuple, Suggestion]] = []
    for week_offset in range(HORIZON_WEEKS):
        for k in range(6):
            d = anchor + timedelta(days=7 * week_offset + k)
            if _check_date(comp, d):
                continue
            day = env.day(d)
            busy = day.teacher_busy.get(comp.teacher_id, set())
            load = len(busy)
            busy_ords = {env.ordinal[s] for s in busy}
            for slot_ids in _candidate_groups(env, comp, d.weekday()):
                if _check_core(env, comp, d, slot_ids):
                    continue
                rooms = _free_rooms(env, comp, d, slot_ids)
                if not rooms:
                    continue
                cand_ords = [env.ordinal[s] for s in slot_ids]
                adjacent = any((o - 1 in busy_ords) or (o + 1 in busy_ords) for o in cand_ords)
                first = env.slot_by_id[slot_ids[0]]
                last = env.slot_by_id[slot_ids[-1]]
                room = env.room_by_id[rooms[0]]
                reason = (
                    f"Week +{week_offset}, teacher has {load} period(s) that day"
                    + (", next to an existing class" if adjacent else "")
                )
                sug = Suggestion(
                    date=d,
                    day_name=DAY_NAMES[d.weekday()],
                    time_slot_id=slot_ids[0],
                    time_slot2_id=slot_ids[1] if len(slot_ids) > 1 else None,
                    period_label=_label_for([first, last] if len(slot_ids) > 1 else [first], ordinals),
                    start_time=first.start_time,
                    end_time=last.end_time,
                    room_id=room.id,
                    room=room.name,
                    week_offset=week_offset,
                    teacher_load_that_day=load,
                    reason=reason,
                )
                key = (week_offset, d, load, 0 if adjacent else 1, first.period_index)
                ranked.append((key, sug))
    ranked.sort(key=lambda t: t[0])
    return [s for _, s in ranked[:limit]]


def _resolve_slots(
    env: _Env, comp: Compensation, d: date, slot_id: int, slot2_id: int | None
) -> tuple[list[int], str | None]:
    s1 = env.slot_by_id.get(slot_id)
    if s1 is None:
        return [], "Unknown time slot."
    if comp.periods == 2:
        if slot2_id is None:
            return [], "This is a 2-period lab class: choose two consecutive periods."
        s2 = env.slot_by_id.get(slot2_id)
        if s2 is None:
            return [], "Unknown time slot."
        pair = sorted([s1, s2], key=lambda s: s.period_index)
        if pair[0].day_of_week != pair[1].day_of_week or pair[1].period_index - pair[0].period_index != 1:
            return [], "A lab class needs two consecutive periods on the same day."
        slots = pair
    else:
        if slot2_id is not None:
            return [], "This make-up is a single period."
        slots = [s1]
    if any(s.day_of_week != d.weekday() for s in slots):
        return [], "The chosen period does not fall on the chosen date's weekday."
    return [s.id for s in slots], None


def validate_slot(
    db: Session, comp: Compensation, d: date, slot_id: int, slot2_id: int | None, room_id: int | None
) -> tuple[int | None, str | None]:
    """Return (room_id, None) if the slot is valid else (None, reason). No horizon cap."""
    env = _Env(db, comp.id)
    slot_ids, err = _resolve_slots(env, comp, d, slot_id, slot2_id)
    if err:
        return None, err
    err = _check_core(env, comp, d, slot_ids)
    if err:
        return None, err
    free = _free_rooms(env, comp, d, slot_ids)
    if room_id is not None:
        room = env.room_by_id.get(room_id)
        if room is None:
            return None, "Unknown room."
        if room.is_lab != comp.is_lab:
            return None, f"{room.name} is the wrong room type for this class."
        if room_id not in free:
            return None, f"{room.name} is already in use in that period."
        return room_id, None
    if not free:
        return None, "No suitable room is free in that period."
    return free[0], None


def apply_slot(
    db: Session, comp: Compensation, d: date, slot_id: int, slot2_id: int | None, room_id: int | None
) -> str | None:
    """Validate then set the proposed slot on comp. Returns an error reason or None."""
    room, err = validate_slot(db, comp, d, slot_id, slot2_id, room_id)
    if err:
        return err
    env = _Env(db, comp.id)
    slot_ids, _ = _resolve_slots(env, comp, d, slot_id, slot2_id)
    _set_slot(comp, d, slot_ids, room)
    return None


def _set_slot(comp: Compensation, d: date | None, slot_ids: list[int], room_id: int | None) -> None:
    comp.proposed_date = d
    comp.proposed_time_slot_id = slot_ids[0] if slot_ids else None
    comp.proposed_time_slot2_id = slot_ids[1] if len(slot_ids) > 1 else None
    comp.room_id = room_id
    comp.updated_at = _now()


def _set_from_suggestion(comp: Compensation, s: Suggestion | None) -> None:
    if s is None:
        _set_slot(comp, None, [], None)
        comp.notes = NO_SLOT_NOTE
    else:
        _set_slot(comp, s.date, [s.time_slot_id] + ([s.time_slot2_id] if s.time_slot2_id else []), s.room_id)
        if comp.notes == NO_SLOT_NOTE:
            comp.notes = None


def repropose(db: Session, comp: Compensation) -> bool:
    """Recompute the best slot and book it automatically.

    Status becomes SCHEDULED when a slot was found, otherwise PROPOSED (waiting
    for a slot; the sweep retries these). Returns True if a slot was found."""
    best = suggest_slots(db, comp, limit=1)
    _set_from_suggestion(comp, best[0] if best else None)
    comp.status = CompensationStatus.SCHEDULED if best else CompensationStatus.PROPOSED
    db.flush()
    return bool(best)


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------
def _hods(db: Session) -> list[Teacher]:
    return list(db.scalars(select(Teacher).where(Teacher.role == Role.HOD, Teacher.is_active.is_(True))).all())


def notify_teacher_and_hods(db: Session, teacher: Teacher, title: str, body: str) -> None:
    notify(db, teacher, title, body)
    for hod in _hods(db):
        if hod.id != teacher.id:
            notify(db, hod, title, f"{teacher.name}: {body}")


def _describe(comp: Compensation) -> str:
    return f"{comp.subject.name} for {comp.class_section.name} (missed {comp.missed_date})"


# --------------------------------------------------------------------------
# Creation
# --------------------------------------------------------------------------
def _referenced_sub_ids(db: Session) -> set[int]:
    ids: set[int] = set()
    for a, b in db.execute(select(Compensation.substitution_id, Compensation.substitution2_id)).all():
        if a:
            ids.add(a)
        if b:
            ids.add(b)
    return ids


def _new_comp(sub: Substitution, sub2: Substitution | None, is_lab: bool, periods: int) -> Compensation:
    e = sub.timetable_entry
    return Compensation(
        leave_id=sub.leave_id,
        substitution_id=sub.id,
        substitution2_id=sub2.id if sub2 else None,
        teacher_id=sub.absent_teacher_id,
        subject_id=e.subject_id,
        class_section_id=e.class_section_id,
        is_lab=is_lab,
        missed_date=sub.override_date,
        missed_time_slot_id=e.time_slot_id,
        missed_time_slot2_id=sub2.timetable_entry.time_slot_id if sub2 else None,
        periods=periods,
        status=CompensationStatus.PROPOSED,
    )


def create_for_substitutions(db: Session, subs: list[Substitution], actor_id: int | None = None) -> list[Compensation]:
    """Create PROPOSED compensations for ASSIGNED/UNCOVERED substitutions (idempotent)."""
    done = _referenced_sub_ids(db)
    todo = [
        s for s in subs
        if s.status in (SubstitutionStatus.ASSIGNED, SubstitutionStatus.UNCOVERED) and s.id not in done
    ]
    todo.sort(key=lambda s: (s.override_date, s.id))

    groups: dict[tuple, list[Substitution]] = {}
    order: list[tuple] = []
    for s in todo:
        e = s.timetable_entry
        key = (s.leave_id, e.block_id, s.override_date, s.absent_teacher_id) if (e.is_double and e.block_id) else ("single", s.id)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(s)

    created: list[Compensation] = []

    def add(comp: Compensation) -> None:
        best = suggest_slots(db, comp, limit=1)
        _set_from_suggestion(comp, best[0] if best else None)
        # Automatic: book the slot straight away; only unplaceable ones wait.
        comp.status = CompensationStatus.SCHEDULED if best else CompensationStatus.PROPOSED
        db.add(comp)
        db.flush()  # later records see this reservation
        created.append(comp)

    for key in order:
        members = groups[key]
        if key[0] == "single" or len(members) == 1:
            s = members[0]
            add(_new_comp(s, None, bool(s.timetable_entry.is_double), 1))
            continue
        members.sort(key=lambda s: s.timetable_entry.time_slot.period_index)
        a, b = members[0], members[1]
        consecutive = (
            b.timetable_entry.time_slot.period_index - a.timetable_entry.time_slot.period_index == 1
            and a.timetable_entry.time_slot.day_of_week == b.timetable_entry.time_slot.day_of_week
        )
        if consecutive:
            pair = _new_comp(a, b, True, 2)
            if suggest_slots(db, pair, limit=1):
                add(pair)
                for extra in members[2:]:
                    add(_new_comp(extra, None, True, 1))
                continue
        for s in members:
            add(_new_comp(s, None, True, 1))

    if created:
        by_teacher: dict[int, list[Compensation]] = {}
        for c in created:
            audit.log(db, actor_id=actor_id,
                      action="COMP_SCHEDULED" if c.proposed_date else "COMP_PROPOSED",
                      entity="compensation", entity_id=c.id,
                      detail=_describe(c) + (f" -> auto-scheduled {c.proposed_date}" if c.proposed_date else " -> no slot found"))
            by_teacher.setdefault(c.teacher_id, []).append(c)
        for tid, comps in by_teacher.items():
            teacher = db.get(Teacher, tid)
            placed = [c for c in comps if c.proposed_date is not None]
            unplaced = len(comps) - len(placed)
            lines = []
            for c in placed:
                out = to_out(c)
                lines.append(f"{c.subject.name} ({c.class_section.name}) on {out.proposed_date} {out.proposed_period}")
            body = ""
            if placed:
                body = f"{sum(c.periods for c in placed)} make-up period(s) scheduled automatically: " + "; ".join(lines) + "."
            if unplaced:
                body += f" {unplaced} could not be placed yet and will be retried."
            notify_teacher_and_hods(db, teacher, "Make-up classes scheduled" if placed else "Make-up classes pending", body.strip())
    return created


def ensure_for_substitution(db: Session, sub: Substitution) -> list[Compensation]:
    """Create the compensation for a single substitution if none exists yet."""
    return create_for_substitutions(db, [sub], actor_id=None)


def backfill(db: Session, actor_id: int | None) -> tuple[int, int, int]:
    """Create compensations for every ASSIGNED/UNCOVERED substitution without one.
    Returns (records created, periods, skipped)."""
    subs = db.scalars(
        select(Substitution).where(
            Substitution.status.in_((SubstitutionStatus.ASSIGNED, SubstitutionStatus.UNCOVERED))
        )
    ).all()
    done = _referenced_sub_ids(db)
    skipped = sum(1 for s in subs if s.id in done)
    created = create_for_substitutions(db, list(subs), actor_id=actor_id)
    periods = sum(c.periods for c in created)
    audit.log(db, actor_id=actor_id, action="COMP_BACKFILL", entity="compensation", entity_id=None,
              detail=f"Created {len(created)} record(s) / {periods} period(s); skipped {skipped}.")
    return len(created), periods, skipped


# --------------------------------------------------------------------------
# Lifecycle hooks
# --------------------------------------------------------------------------
def cancel_for_leave(db: Session, leave: Leave, actor_id: int | None) -> int:
    comps = db.scalars(
        select(Compensation).where(Compensation.leave_id == leave.id, Compensation.status.in_(ACTIVE_STATUSES))
    ).all()
    for c in comps:
        was_scheduled = c.status == CompensationStatus.SCHEDULED
        c.status = CompensationStatus.CANCELLED
        c.notes = "Leave cancelled"
        c.updated_at = _now()
        audit.log(db, actor_id=actor_id, action="COMP_CANCELLED", entity="compensation", entity_id=c.id,
                  detail="Leave cancelled: " + _describe(c))
        if was_scheduled:
            notify(db, c.teacher, "Make-up class cancelled",
                   f"The make-up for {_describe(c)} on {c.proposed_date} is no longer needed (leave cancelled).")
    return len(comps)


def handle_new_leave_conflicts(db: Session, leave: Leave) -> None:
    """A new leave makes that date unusable for the teacher's existing make-ups."""
    comps = db.scalars(
        select(Compensation).where(
            Compensation.teacher_id == leave.teacher_id,
            Compensation.proposed_date == leave.leave_date,
            Compensation.status.in_(ACTIVE_STATUSES),
        )
    ).all()
    teacher = db.get(Teacher, leave.teacher_id)
    for c in comps:
        was_scheduled = c.status == CompensationStatus.SCHEDULED
        found = repropose(db, c)  # automatically moves it to the next free slot
        audit.log(db, actor_id=None, action="COMP_RESCHEDULED", entity="compensation", entity_id=c.id,
                  detail=f"Moved automatically after new leave on {leave.leave_date}.")
        if was_scheduled:
            out = to_out(c)
            where = f"{out.proposed_date} {out.proposed_period}" if found else "a slot to be found"
            notify_teacher_and_hods(db, teacher, "Make-up class moved",
                                    f"{_describe(c)} was moved because of your leave on {leave.leave_date}. New time: {where}.")


def sweep_past(db: Session) -> bool:
    """Auto-complete finished SCHEDULED make-ups; re-propose stale PROPOSED ones."""
    today = date.today()
    changed = False
    for c in db.scalars(select(Compensation).where(Compensation.status == CompensationStatus.SCHEDULED,
                                                    Compensation.proposed_date < today)).all():
        c.status = CompensationStatus.COMPLETED
        c.notes = "Auto-completed"
        c.updated_at = _now()
        audit.log(db, actor_id=None, action="COMP_COMPLETED", entity="compensation", entity_id=c.id,
                  detail="Auto-completed: " + _describe(c))
        changed = True
    stale = db.scalars(select(Compensation).where(
        Compensation.status == CompensationStatus.PROPOSED,
        (Compensation.proposed_date.is_(None)) | (Compensation.proposed_date < today),
    )).all()
    for c in stale:
        before = (c.proposed_date, c.proposed_time_slot_id, c.proposed_time_slot2_id, c.room_id)
        repropose(db, c)
        if before != (c.proposed_date, c.proposed_time_slot_id, c.proposed_time_slot2_id, c.room_id):
            changed = True
    return changed


def active_comp_slots(db: Session, d: date) -> dict[int, set[int]]:
    """teacher_id -> slot ids held by PROPOSED/SCHEDULED make-ups on date d."""
    result: dict[int, set[int]] = {}
    for c in db.scalars(select(Compensation).where(
        Compensation.proposed_date == d, Compensation.status.in_(ACTIVE_STATUSES)
    )).all():
        for sid in (c.proposed_time_slot_id, c.proposed_time_slot2_id):
            if sid is not None:
                result.setdefault(c.teacher_id, set()).add(sid)
    return result


# --------------------------------------------------------------------------
# Serialisation
# --------------------------------------------------------------------------
def period_ordinals(db: Session) -> dict[int, int]:
    return _ordinal_map(list(db.scalars(select(TimeSlot)).all()))


def to_out(comp: Compensation, ordinals: dict[int, int] | None = None) -> CompensationOut:
    if ordinals is None:
        ordinals = period_ordinals(object_session(comp))
    missed = [comp.missed_time_slot] + ([comp.missed_time_slot2] if comp.missed_time_slot2 else [])
    proposed = None
    if comp.proposed_time_slot:
        proposed = [comp.proposed_time_slot] + ([comp.proposed_time_slot2] if comp.proposed_time_slot2 else [])
    if proposed:
        proposed.sort(key=lambda s: s.period_index)
    can_complete = (
        comp.status == CompensationStatus.SCHEDULED
        and comp.proposed_date is not None
        and comp.proposed_date <= date.today()
    )
    return CompensationOut(
        id=comp.id,
        leave_id=comp.leave_id,
        substitution_id=comp.substitution_id,
        teacher_id=comp.teacher_id,
        teacher=comp.teacher.name,
        subject=comp.subject.name,
        class_section=comp.class_section.name,
        class_section_id=comp.class_section_id,
        is_lab=comp.is_lab,
        missed_date=comp.missed_date,
        missed_period=_label_for(missed, ordinals),
        missed_day_of_week=comp.missed_date.weekday(),
        periods=comp.periods,
        proposed_date=comp.proposed_date,
        proposed_day_of_week=comp.proposed_date.weekday() if comp.proposed_date else None,
        proposed_period=_label_for(proposed, ordinals) if proposed else None,
        proposed_start_time=proposed[0].start_time if proposed else None,
        proposed_end_time=proposed[-1].end_time if proposed else None,
        proposed_time_slot_id=comp.proposed_time_slot_id,
        proposed_time_slot2_id=comp.proposed_time_slot2_id,
        room=comp.room.name if comp.room else None,
        room_id=comp.room_id,
        status=comp.status,
        notes=comp.notes,
        created_at=comp.created_at,
        can_complete=can_complete,
    )
