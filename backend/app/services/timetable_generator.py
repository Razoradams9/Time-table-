"""Base timetable generation using OR-Tools CP-SAT (Requirement 2).

Model overview
--------------
We create a "requirement" for every (class_section, subject, occurrence) that
must be scheduled `periods_per_week` times. For each requirement we choose:
  - a time slot,
  - a qualified teacher,
  - a suitable room.

Hard constraints:
  - No class is double-booked in a slot.
  - No teacher teaches two things in the same slot.
  - No room hosts two things in the same slot.
  - A teacher is only assigned in slots they are available for.
  - A teacher never exceeds their max periods per day.
  - Lab subjects go to lab rooms and to teachers qualified for the subject.
  - The same subject for a class is not scheduled twice in one day (spread out).

Soft objective (maximised):
  - High-importance subjects placed in preferred slots.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ortools.sat.python import cp_model
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Availability,
    ClassSection,
    Room,
    Subject,
    Teacher,
    TimeSlot,
    TimetableEntry,
)


@dataclass
class GenOutcome:
    success: bool
    version: int | None = None
    entries: int = 0
    message: str = ""
    conflicts: list[str] = field(default_factory=list)


def _teacher_available_slots(db: Session) -> dict[int, set[int]]:
    """teacher_id -> set of slot ids they can teach.

    If a teacher has no availability rows, they are available everywhere.
    """
    all_slot_ids = {s.id for s in db.scalars(select(TimeSlot)).all()}
    rows = db.scalars(select(Availability)).all()
    declared: dict[int, set[int]] = {}
    for r in rows:
        declared.setdefault(r.teacher_id, set()).add(r.time_slot_id)

    result: dict[int, set[int]] = {}
    for t in db.scalars(select(Teacher)).all():
        result[t.id] = declared.get(t.id, set(all_slot_ids))
    return result


def generate_timetable(db: Session, max_seconds: float = 20.0) -> GenOutcome:
    slots = db.scalars(select(TimeSlot)).all()
    subjects = db.scalars(select(Subject)).all()
    classes = db.scalars(select(ClassSection)).all()
    rooms = db.scalars(select(Room)).all()
    teachers = db.scalars(select(Teacher)).all()

    conflicts: list[str] = []
    if not slots:
        conflicts.append("No time slots defined.")
    if not classes:
        conflicts.append("No class sections defined.")
    if not subjects:
        conflicts.append("No subjects defined.")
    if not rooms:
        conflicts.append("No rooms defined.")
    if not teachers:
        conflicts.append("No teachers defined.")
    if conflicts:
        return GenOutcome(success=False, message="Missing base data.", conflicts=conflicts)

    avail = _teacher_available_slots(db)
    lab_rooms = [r for r in rooms if r.is_lab]
    normal_rooms = [r for r in rooms if not r.is_lab]

    # Qualified teachers per subject.
    qualified: dict[int, list[int]] = {}
    for subj in subjects:
        qteachers = [t.id for t in subj.teachers]
        qualified[subj.id] = qteachers

    # Pre-flight feasibility checks with clear messages (Req 2.6).
    for subj in subjects:
        if not qualified[subj.id]:
            conflicts.append(f"Subject '{subj.name}' has no qualified teacher assigned.")
        if subj.is_lab and not lab_rooms:
            conflicts.append(f"Lab subject '{subj.name}' needs a lab room, but none exist.")
        if not subj.is_lab and not normal_rooms:
            conflicts.append(f"Subject '{subj.name}' needs a classroom, but none exist.")
    if conflicts:
        return GenOutcome(success=False, message="Data cannot satisfy constraints.", conflicts=conflicts)

    slots_by_day: dict[int, list[TimeSlot]] = {}
    for s in slots:
        slots_by_day.setdefault(s.day_of_week, []).append(s)

    model = cp_model.CpModel()

    # Build requirements: one per (class, subject, occurrence).
    # x[(req, slot, teacher, room)] = 1 if that assignment is chosen.
    @dataclass
    class Req:
        key: str
        class_id: int
        subject: Subject

    requirements: list[Req] = []
    for cls in classes:
        for subj in subjects:
            for occ in range(subj.periods_per_week):
                requirements.append(Req(key=f"c{cls.id}_s{subj.id}_o{occ}", class_id=cls.id, subject=subj))

    # Decision vars.
    x: dict[tuple[int, int, int, int], cp_model.IntVar] = {}
    # Indexes for constraints.
    by_req: dict[int, list[tuple[int, int, int, int]]] = {}
    by_class_slot: dict[tuple[int, int], list] = {}
    by_teacher_slot: dict[tuple[int, int], list] = {}
    by_room_slot: dict[tuple[int, int], list] = {}
    by_teacher_day: dict[tuple[int, int], list] = {}
    by_reqday: dict[tuple[int, int], list] = {}  # (req_idx, day) -> vars, to spread subjects

    slot_day = {s.id: s.day_of_week for s in slots}
    preferred = {s.id: s.is_preferred for s in slots}

    for ri, req in enumerate(requirements):
        subj = req.subject
        candidate_rooms = lab_rooms if subj.is_lab else normal_rooms
        candidate_teachers = qualified[subj.id]
        for s in slots:
            for tid in candidate_teachers:
                if s.id not in avail.get(tid, set()):
                    continue
                for room in candidate_rooms:
                    var = model.NewBoolVar(f"x_{ri}_{s.id}_{tid}_{room.id}")
                    x[(ri, s.id, tid, room.id)] = var
                    by_req.setdefault(ri, []).append((ri, s.id, tid, room.id))
                    by_class_slot.setdefault((req.class_id, s.id), []).append(var)
                    by_teacher_slot.setdefault((tid, s.id), []).append(var)
                    by_room_slot.setdefault((room.id, s.id), []).append(var)
                    by_teacher_day.setdefault((tid, slot_day[s.id]), []).append(var)
                    by_reqday.setdefault((ri, slot_day[s.id]), []).append(var)

    # Each requirement scheduled exactly once.
    for ri, req in enumerate(requirements):
        keys = by_req.get(ri)
        if not keys:
            conflicts.append(
                f"Cannot place '{req.subject.name}' for a class: no qualified+available teacher/room/slot combo."
            )
            continue
        model.AddExactlyOne(x[k] for k in keys)
    if conflicts:
        return GenOutcome(success=False, message="Some requirements are impossible to place.", conflicts=conflicts)

    # No class double-booked.
    for (_cls, _slot), vars_ in by_class_slot.items():
        model.AddAtMostOne(vars_)
    # No teacher double-booked.
    for (_t, _slot), vars_ in by_teacher_slot.items():
        model.AddAtMostOne(vars_)
    # No room double-booked.
    for (_r, _slot), vars_ in by_room_slot.items():
        model.AddAtMostOne(vars_)

    # Teacher max periods per day.
    teacher_by_id = {t.id: t for t in teachers}
    for (tid, _day), vars_ in by_teacher_day.items():
        cap = teacher_by_id[tid].max_periods_per_day
        model.Add(sum(vars_) <= cap)

    # Spread: a subject for a class at most once per day.
    for (_ri, _day), vars_ in by_reqday.items():
        model.AddAtMostOne(vars_)

    # Objective: reward important subjects in preferred slots.
    objective_terms = []
    for (ri, sid, tid, rid), var in x.items():
        subj = requirements[ri].subject
        weight = subj.importance * (3 if preferred.get(sid) else 0)
        if weight:
            objective_terms.append(weight * var)
    if objective_terms:
        model.Maximize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_seconds
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return GenOutcome(
            success=False,
            message="No valid timetable could be produced within the time limit. "
            "Try relaxing availability, adding rooms/teachers, or reducing periods per week.",
            conflicts=["Constraints are over-tight (double-booking / availability / capacity)."],
        )

    # Determine new version and deactivate previous active timetable.
    prev_max = db.scalar(select(TimetableEntry.version).order_by(TimetableEntry.version.desc()))
    version = (prev_max or 0) + 1

    chosen = [(ri, sid, tid, rid) for (ri, sid, tid, rid), var in x.items() if solver.Value(var) == 1]

    count = 0
    for ri, sid, tid, rid in chosen:
        req = requirements[ri]
        entry = TimetableEntry(
            version=version,
            is_active=False,  # activated on approval (Req 2.7)
            time_slot_id=sid,
            teacher_id=tid,
            subject_id=req.subject.id,
            class_section_id=req.class_id,
            room_id=rid,
        )
        db.add(entry)
        count += 1

    return GenOutcome(
        success=True,
        version=version,
        entries=count,
        message=f"Generated timetable v{version} with {count} entries. Approve to lock it as the base.",
    )
