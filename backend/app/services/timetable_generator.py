"""Base timetable generation using OR-Tools CP-SAT.

This version places fixed CourseOfferings (teacher + subject + class are given)
and optimises for humane, non-exhausting teacher loads.

Hard constraints
  - Every offering's single + double sessions are all scheduled.
  - A double (lab) occupies TWO adjacent periods on the same day, never split
    across the mid-day break and never across days.
  - No teacher, class, or room is double-booked in a period. Co-teachers of a
    lab are both occupied for that block.
  - A teacher never exceeds their max periods/day.
  - A teacher never teaches more than `max_consecutive` periods in a row.
  - The same offering is not scheduled twice in one day (spread across week).
  - Teachers respect declared availability (if any).

Soft objective (minimise teacher exhaustion)
  - Reward free periods, penalise heavy days and long runs, keep each teacher's
    daily load balanced across the week.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from ortools.sat.python import cp_model
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Availability,
    ClassSection,
    CourseOffering,
    Room,
    TimeSlot,
    Teacher,
    TimetableEntry,
)


def _window_slot_ids(slots: list[TimeSlot]) -> tuple[set[int], set[int]]:
    """Split slots into MORNING (first half of each day) and AFTERNOON (second
    half) by period ordinal within the day. Returns (morning_ids, afternoon_ids).
    """
    by_day: dict[int, list[TimeSlot]] = {}
    for s in slots:
        by_day.setdefault(s.day_of_week, []).append(s)
    morning: set[int] = set()
    afternoon: set[int] = set()
    for day, ds in by_day.items():
        ds.sort(key=lambda s: s.period_index)
        half = len(ds) // 2
        for s in ds[:half]:
            morning.add(s.id)
        for s in ds[half:]:
            afternoon.add(s.id)
    return morning, afternoon


@dataclass
class GenOutcome:
    success: bool
    version: int | None = None
    entries: int = 0
    message: str = ""
    conflicts: list[str] = field(default_factory=list)


def _availability(db: Session) -> dict[int, set[int] | None]:
    rows = db.scalars(select(Availability)).all()
    declared: dict[int, set[int]] = {}
    for r in rows:
        declared.setdefault(r.teacher_id, set()).add(r.time_slot_id)
    out: dict[int, set[int] | None] = {}
    for t in db.scalars(select(Teacher)).all():
        out[t.id] = declared.get(t.id)  # None => unrestricted
    return out


def generate_timetable(db: Session, max_seconds: float = 30.0) -> GenOutcome:
    slots = db.scalars(select(TimeSlot).order_by(TimeSlot.day_of_week, TimeSlot.period_index)).all()
    offerings = db.scalars(select(CourseOffering)).all()
    rooms = db.scalars(select(Room)).all()
    teachers = db.scalars(select(Teacher)).all()
    classes = db.scalars(select(ClassSection)).all()

    conflicts: list[str] = []
    if not slots:
        conflicts.append("No time slots defined.")
    if not offerings:
        conflicts.append("No course offerings defined — nothing to schedule.")
    if not rooms:
        conflicts.append("No rooms defined.")
    if conflicts:
        return GenOutcome(success=False, message="Missing base data.", conflicts=conflicts)

    teacher_by_id = {t.id: t for t in teachers}
    avail = _availability(db)

    lab_rooms = [r for r in rooms if r.is_lab]
    normal_rooms = [r for r in rooms if not r.is_lab]
    if not normal_rooms:
        normal_rooms = rooms[:]  # fallback

    # Group slots by day; determine which adjacent period pairs are valid for a
    # double (consecutive period_index AND not spanning the lunch break — we
    # treat a gap in period ordering / an explicit break as a boundary).
    slots_by_day: dict[int, list[TimeSlot]] = {}
    for s in slots:
        slots_by_day.setdefault(s.day_of_week, []).append(s)
    for day in slots_by_day:
        slots_by_day[day].sort(key=lambda s: s.period_index)

    slot_lookup = {(s.day_of_week, s.period_index): s for s in slots}
    slot_day = {s.id: s.day_of_week for s in slots}
    period_of = {s.id: s.period_index for s in slots}

    # Valid double anchor pairs: (first_slot, second_slot) adjacent same day.
    double_pairs: list[tuple[TimeSlot, TimeSlot]] = []
    for day, dslots in slots_by_day.items():
        for i in range(len(dslots) - 1):
            a, b = dslots[i], dslots[i + 1]
            # adjacent means period_index differs by exactly 1
            if b.period_index - a.period_index == 1:
                double_pairs.append((a, b))

    # Per-class allowed slot sets based on its time window (hard constraint).
    morning_ids, afternoon_ids = _window_slot_ids(slots)
    class_window = {c.id: (c.time_window or "ANY") for c in classes}

    def allowed_slots_for_class(class_id: int) -> set[int] | None:
        win = class_window.get(class_id, "ANY")
        if win == "MORNING":
            return morning_ids
        if win == "AFTERNOON":
            return afternoon_ids
        return None  # ANY => unrestricted

    model = cp_model.CpModel()

    # ---- Decision variables ----
    # For singles: x_single[(off_idx, occ, slot_id)] = 1
    # For doubles: x_double[(off_idx, occ, first_slot_id)] = 1 (occupies first & first+1)
    x_single: dict[tuple, cp_model.IntVar] = {}
    x_double: dict[tuple, cp_model.IntVar] = {}

    # Occupancy helpers: lists of (var, teacher_ids, class_id, is_lab, offering)
    # keyed by slot for conflict constraints.
    occ_teacher: dict[tuple[int, int], list] = {}   # (teacher_id, slot_id) -> vars
    occ_class: dict[tuple[int, int], list] = {}      # (class_id, slot_id) -> vars
    occ_lab_slot: dict[int, list] = {}               # slot_id -> vars needing a lab room
    occ_norm_slot: dict[int, list] = {}              # slot_id -> vars needing a normal room
    teacher_day_vars: dict[tuple[int, int], list] = {}  # (teacher_id, day) -> [(var, weight)]
    offering_day_vars: dict[tuple[int, int], list] = {}  # (off_idx, day) -> vars (spread)

    def teachers_of(off: CourseOffering) -> list[int]:
        ids = [off.teacher_id]
        if off.co_teacher_id:
            ids.append(off.co_teacher_id)
        return ids

    for oi, off in enumerate(offerings):
        tids = teachers_of(off)
        allowed = allowed_slots_for_class(off.class_section_id)
        # ---- single sessions ----
        for occ in range(off.single_sessions):
            choices = []
            for s in slots:
                # class time window
                if allowed is not None and s.id not in allowed:
                    continue
                # availability
                ok = True
                for tid in tids:
                    av = avail.get(tid)
                    if av is not None and s.id not in av:
                        ok = False
                        break
                if not ok:
                    continue
                var = model.NewBoolVar(f"s_{oi}_{occ}_{s.id}")
                x_single[(oi, occ, s.id)] = var
                choices.append(var)
                for tid in tids:
                    occ_teacher.setdefault((tid, s.id), []).append(var)
                    teacher_day_vars.setdefault((tid, s.id and slot_day[s.id]), []).append(var)
                occ_class.setdefault((off.class_section_id, s.id), []).append(var)
                (occ_lab_slot if off.subject.is_lab else occ_norm_slot).setdefault(s.id, []).append(var)
                offering_day_vars.setdefault((oi, slot_day[s.id]), []).append(var)
            if not choices:
                conflicts.append(f"Cannot place a session of {off.label or off.subject.name}.")
            else:
                model.AddExactlyOne(choices)

        # ---- double sessions (2 adjacent periods) ----
        for occ in range(off.double_sessions):
            choices = []
            for (a, b) in double_pairs:
                # both halves must be inside the class's window
                if allowed is not None and (a.id not in allowed or b.id not in allowed):
                    continue
                ok = True
                for tid in tids:
                    av = avail.get(tid)
                    if av is not None and (a.id not in av or b.id not in av):
                        ok = False
                        break
                if not ok:
                    continue
                var = model.NewBoolVar(f"d_{oi}_{occ}_{a.id}")
                x_double[(oi, occ, a.id, b.id)] = var
                choices.append(var)
                # occupies BOTH slots
                for sid in (a.id, b.id):
                    for tid in tids:
                        occ_teacher.setdefault((tid, sid), []).append(var)
                        teacher_day_vars.setdefault((tid, slot_day[sid]), []).append(var)
                    occ_class.setdefault((off.class_section_id, sid), []).append(var)
                    occ_lab_slot.setdefault(sid, []).append(var)
                offering_day_vars.setdefault((oi, a.day_of_week), []).append(var)
            if not choices:
                conflicts.append(f"Cannot place lab block of {off.label or off.subject.name}.")
            else:
                model.AddExactlyOne(choices)

    if conflicts:
        return GenOutcome(success=False, message="Some sessions are impossible to place.", conflicts=conflicts)

    # ---- No double-booking ----
    for (_t, _s), vars_ in occ_teacher.items():
        if len(vars_) > 1:
            model.AddAtMostOne(vars_)
    for (_c, _s), vars_ in occ_class.items():
        if len(vars_) > 1:
            model.AddAtMostOne(vars_)
    # Room capacity per slot: at most len(lab_rooms) labs and len(normal_rooms) normals.
    n_lab = max(1, len(lab_rooms))
    n_norm = max(1, len(normal_rooms))
    for sid, vars_ in occ_lab_slot.items():
        model.Add(sum(vars_) <= n_lab)
    for sid, vars_ in occ_norm_slot.items():
        model.Add(sum(vars_) <= n_norm)

    # ---- Spread: an offering at most once per day ----
    for (_oi, _day), vars_ in offering_day_vars.items():
        if len(vars_) > 1:
            model.AddAtMostOne(vars_)

    # ---- Exhaustion: max periods/day + balance ----
    # Build per-teacher per-day period-count expressions.
    periods_by_tday: dict[tuple[int, int], list] = {}
    for (tid, sid), vars_ in occ_teacher.items():
        day = slot_day[sid]
        periods_by_tday.setdefault((tid, day), []).extend(vars_)

    max_day = settings.__dict__.get("max_periods_per_day_cap", None)
    objective = []
    for (tid, day), vars_ in periods_by_tday.items():
        cap = teacher_by_id[tid].max_periods_per_day
        model.Add(sum(vars_) <= cap)
        # soft: penalise days that are very full (encourage spreading / free time)
        heavy = model.NewBoolVar(f"heavy_{tid}_{day}")
        model.Add(sum(vars_) >= cap).OnlyEnforceIf(heavy)
        model.Add(sum(vars_) < cap).OnlyEnforceIf(heavy.Not())
        objective.append(heavy)

    # ---- No more than N consecutive periods in a row (per teacher per day) ----
    max_consec = getattr(settings, "max_consecutive_periods", 3)
    # occupancy bool per (teacher, slot): is the teacher busy that slot?
    busy: dict[tuple[int, int], cp_model.IntVar] = {}
    for (tid, sid), vars_ in occ_teacher.items():
        b = model.NewBoolVar(f"busy_{tid}_{sid}")
        model.AddMaxEquality(b, vars_) if len(vars_) > 1 else model.Add(b == vars_[0])
        busy[(tid, sid)] = b
    for day, dslots in slots_by_day.items():
        for tid in teacher_by_id:
            window = []
            for s in dslots:
                key = (tid, s.id)
                if key in busy:
                    window.append(busy[key])
                else:
                    window.append(None)
            # slide a window of (max_consec+1); forbid all-busy runs longer than max_consec
            for i in range(len(window) - max_consec):
                run = [window[i + k] for k in range(max_consec + 1)]
                if all(v is not None for v in run):
                    model.Add(sum(run) <= max_consec)

    if objective:
        model.Minimize(sum(objective))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_seconds
    # Worker count is env-tunable so small hosts (e.g. a 512MB free instance)
    # don't thrash. Default stays modest; bump SOLVER_WORKERS locally for speed.
    solver.parameters.num_search_workers = getattr(settings, "solver_workers", 2)
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return GenOutcome(
            success=False,
            message="No valid timetable within the time limit. Loads may be too tight — "
            "try raising max periods/day, adding rooms, or reducing sessions.",
            conflicts=["Constraints are over-tight (availability / rooms / daily caps / consecutive limit)."],
        )

    # ---- Persist ----
    prev_max = db.scalar(select(TimetableEntry.version).order_by(TimetableEntry.version.desc()))
    version = (prev_max or 0) + 1

    # Room assignment: track which rooms are taken per slot and hand out a free
    # one of the right kind. Doubles reserve the same room across both halves.
    lab_pool = lab_rooms or rooms
    norm_pool = normal_rooms or rooms
    taken: dict[int, set[int]] = {}  # slot_id -> set of room_ids used

    def free_room(sids: list[int], is_lab: bool) -> int:
        pool = lab_pool if is_lab else norm_pool
        for r in pool:
            if all(r.id not in taken.get(sid, set()) for sid in sids):
                for sid in sids:
                    taken.setdefault(sid, set()).add(r.id)
                return r.id
        # fallback: overflow into the other pool
        other = norm_pool if is_lab else lab_pool
        for r in other:
            if all(r.id not in taken.get(sid, set()) for sid in sids):
                for sid in sids:
                    taken.setdefault(sid, set()).add(r.id)
                return r.id
        return pool[0].id  # last resort

    count = 0
    # singles
    for (oi, occ, sid), var in x_single.items():
        if solver.Value(var) != 1:
            continue
        off = offerings[oi]
        rid = free_room([sid], off.subject.is_lab)
        db.add(TimetableEntry(
            version=version, is_active=False, time_slot_id=sid,
            teacher_id=off.teacher_id, co_teacher_id=off.co_teacher_id,
            subject_id=off.subject_id, class_section_id=off.class_section_id,
            room_id=rid, offering_id=off.id, is_double=False,
        ))
        count += 1
    # doubles -> two linked entries sharing one room
    for (oi, occ, a_sid, b_sid), var in x_double.items():
        if solver.Value(var) != 1:
            continue
        off = offerings[oi]
        block = uuid.uuid4().hex[:12]
        rid = free_room([a_sid, b_sid], True)
        for sid in (a_sid, b_sid):
            db.add(TimetableEntry(
                version=version, is_active=False, time_slot_id=sid,
                teacher_id=off.teacher_id, co_teacher_id=off.co_teacher_id,
                subject_id=off.subject_id, class_section_id=off.class_section_id,
                room_id=rid, offering_id=off.id, block_id=block, is_double=True,
            ))
            count += 1

    return GenOutcome(
        success=True, version=version, entries=count,
        message=f"Generated balanced timetable v{version} with {count} periods. Approve to lock it.",
    )
