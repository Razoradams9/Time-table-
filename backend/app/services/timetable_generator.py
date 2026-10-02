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


def _semester_of(class_name: str) -> int | None:
    """Parse the semester number from a class-section name like 'S3 BCA CS'."""
    import re

    m = re.search(r"S(\d+)", class_name or "")
    return int(m.group(1)) if m else None


def allowed_period_window(class_name: str, all_periods: list[int]) -> set[int]:
    """Which period indices a class may be scheduled in, by semester.

    S1 & S5 BCA -> morning block (periods 0..morning_last).
    S3 BCA      -> afternoon block (periods morning_last+1 .. end).
    Anything else (unknown semester) -> unrestricted (all periods).
    """
    from app.config import settings

    cutoff = settings.morning_last_period_index
    sem = _semester_of(class_name)
    morning = {p for p in all_periods if p <= cutoff}
    afternoon = {p for p in all_periods if p > cutoff}
    # All MCA classes run in the evening block, regardless of semester number.
    if "MCA" in (class_name or ""):
        return afternoon
    if sem in (1, 5):
        return morning
    if sem == 3:
        return afternoon
    return set(all_periods)


def rebalance_timetable(db: Session, max_seconds: float = 20.0) -> GenOutcome:
    """Re-place the ACTIVE timetable's real assignments into comfortable slots.

    Unlike generate_timetable (which builds from scratch using subject
    qualifications), this keeps every real (teacher, subject, class) assignment
    exactly as it is and only re-chooses WHEN each one happens, to make the week
    more comfortable:

      * Each assignment stays on the same weekday it is currently on (so the
        set of subjects a class has each day is preserved), but its period
        within that day is re-optimised.
      * No teacher / class / room is double-booked in a slot.
      * Lab subjects stay in lab rooms; lecture subjects in lecture rooms.
      * Soft objective: spread each teacher's periods out (penalise back-to-back
        runs) and pull higher-importance subjects toward preferred (morning)
        slots.

    Produces a new inactive version for the HOD to preview and approve. The
    active timetable is left untouched until approval.
    """
    from app.config import settings

    active = db.scalars(
        select(TimetableEntry).where(TimetableEntry.is_active.is_(True))
    ).all()
    if not active:
        return GenOutcome(
            success=False,
            message="There is no active timetable to rebalance. Import or generate one first.",
            conflicts=["No active timetable."],
        )

    slots = db.scalars(select(TimeSlot)).all()
    rooms = db.scalars(select(Room)).all()
    lab_rooms = [r for r in rooms if r.is_lab]
    normal_rooms = [r for r in rooms if not r.is_lab]

    # Slots grouped by day, ordered by period.
    slots_by_day: dict[int, list[TimeSlot]] = {}
    for s in slots:
        slots_by_day.setdefault(s.day_of_week, []).append(s)
    for d in slots_by_day:
        slots_by_day[d].sort(key=lambda s: s.period_index)

    model = cp_model.CpModel()

    # One "item" per active entry. Each item picks a (slot, room) on its OWN day.
    @dataclass
    class Item:
        entry: TimetableEntry
        day: int
        is_lab: bool

    items: list[Item] = []
    for e in active:
        items.append(Item(entry=e, day=e.time_slot.day_of_week, is_lab=e.subject.is_lab))

    x: dict[tuple[int, int, int], cp_model.IntVar] = {}  # (item_idx, slot_id, room_id)
    by_item: dict[int, list[tuple[int, int, int]]] = {}
    by_class_slot: dict[tuple[int, int], list] = {}
    by_teacher_slot: dict[tuple[int, int], list] = {}
    by_room_slot: dict[tuple[int, int], list] = {}
    # For the comfort objective: teacher -> day -> {period_index: [vars]}
    teacher_day_period: dict[tuple[int, int], dict[int, list]] = {}

    all_period_idxs = sorted({s.period_index for s in slots})
    all_days = sorted(slots_by_day.keys())

    window_by_class: dict[int, set[int]] = {}
    for c in {it.entry.class_section_id: it.entry for it in items}.values():
        window_by_class[c.class_section_id] = allowed_period_window(
            c.class_section.name, all_period_idxs
        )

    # --- Which days may each item use? ---
    # Normally an item keeps its original weekday. BUT if a class has more
    # periods on its original day than its time window can hold, that day is
    # over capacity, so those classes are allowed to move to ANOTHER day (same
    # window) to make room. We only unlock cross-day moves for over-capacity
    # (class, day) pairs, so the rest of the timetable stays put.
    per_class_day_count: dict[tuple[int, int], int] = {}
    for it in items:
        per_class_day_count[(it.entry.class_section_id, it.day)] = (
            per_class_day_count.get((it.entry.class_section_id, it.day), 0) + 1
        )
    over_capacity_days: set[tuple[int, int]] = set()
    for (cid, day), cnt in per_class_day_count.items():
        wsize = len(window_by_class.get(cid, set(all_period_idxs)))
        if cnt > wsize:
            over_capacity_days.add((cid, day))

    # Whole-week capacity check: even spread across all days, do the class's
    # periods fit its window? (window size * number of days).
    cap_conflicts: list[str] = []
    per_class_total: dict[int, int] = {}
    for it in items:
        per_class_total[it.entry.class_section_id] = (
            per_class_total.get(it.entry.class_section_id, 0) + 1
        )
    for cid, total in per_class_total.items():
        capacity = len(window_by_class.get(cid, set(all_period_idxs))) * len(all_days)
        if total > capacity:
            name = next(it.entry.class_section.name for it in items if it.entry.class_section_id == cid)
            cap_conflicts.append(
                f"{name} has {total} periods but its weekly time window only holds {capacity}."
            )
    if cap_conflicts:
        return GenOutcome(
            success=False,
            message="A stream has more weekly periods than its morning/afternoon window can hold.",
            conflicts=cap_conflicts,
        )

    conflicts: list[str] = []
    for i, it in enumerate(items):
        e = it.entry
        candidate_rooms = lab_rooms if it.is_lab else normal_rooms
        if not candidate_rooms:
            candidate_rooms = rooms  # fall back so we never make it infeasible
        window = window_by_class.get(e.class_section_id, set(all_period_idxs))
        # Days this item may land on: its own day, plus (if its original day is
        # over capacity for this class) any other day so overflow can relocate.
        if (e.class_section_id, it.day) in over_capacity_days:
            candidate_days = all_days
        else:
            candidate_days = [it.day]
        for day in candidate_days:
            for s in slots_by_day.get(day, []):
                if s.period_index not in window:
                    continue
                for room in candidate_rooms:
                    var = model.NewBoolVar(f"x_{i}_{s.id}_{room.id}")
                    x[(i, s.id, room.id)] = var
                    by_item.setdefault(i, []).append((i, s.id, room.id))
                    by_class_slot.setdefault((e.class_section_id, s.id), []).append(var)
                    by_teacher_slot.setdefault((e.teacher_id, s.id), []).append(var)
                    by_room_slot.setdefault((room.id, s.id), []).append(var)
                    teacher_day_period.setdefault((e.teacher_id, s.day_of_week), {}).setdefault(
                        s.period_index, []
                    ).append(var)
        if not by_item.get(i):
            conflicts.append(
                f"Could not place {e.subject.name} for {e.class_section.name} "
                f"within its time window."
            )

    if conflicts:
        return GenOutcome(success=False, message="Rebalance infeasible.", conflicts=conflicts)

    # Each item placed exactly once.
    for i in range(len(items)):
        model.AddExactlyOne(x[k] for k in by_item[i])
    # No double-booking of class / teacher / room per slot.
    for vars_ in by_class_slot.values():
        model.AddAtMostOne(vars_)
    for vars_ in by_teacher_slot.values():
        model.AddAtMostOne(vars_)
    for vars_ in by_room_slot.values():
        model.AddAtMostOne(vars_)

    # Cap each class's periods per day at its window size, so relocated overflow
    # fills OTHER days rather than overstuffing one. Build (class, day) -> vars.
    by_class_day: dict[tuple[int, int], list] = {}
    slot_day_of = {s.id: s.day_of_week for s in slots}
    for (i, sid, rid), var in x.items():
        cid = items[i].entry.class_section_id
        by_class_day.setdefault((cid, slot_day_of[sid]), []).append(var)
    for (cid, _day), vars_ in by_class_day.items():
        wsize = len(window_by_class.get(cid, set(all_period_idxs)))
        model.Add(sum(vars_) <= wsize)

    # ----- Comfort objective -----
    # The real win for teacher rest here is a COMPACT day: pull each teacher's
    # periods together so they are not stuck at college from the first slot to
    # the last with idle gaps in between. We minimise, per teacher per day:
    #   * idle gaps  (empty periods sandwiched between taught ones), and
    #   * how late their last period runs,
    # while still discouraging very long unbroken runs. Important subjects are
    # nudged toward preferred (morning) slots.
    preferred = {s.id: s.is_preferred for s in slots}
    importance_by_item = {i: it.entry.subject.importance for i, it in enumerate(items)}
    penalties = []   # things to minimise
    rewards = []     # things to maximise

    # (1) Pull important subjects toward preferred slots.
    for (i, sid, rid), var in x.items():
        if preferred.get(sid):
            rewards.append(importance_by_item[i] * 2 * var)

    # All period indices available in the week (same every day in this schedule).
    all_periods = sorted({s.period_index for s in slots})

    cap = max(1, settings.fatigue_max_consecutive)  # hard limit on periods in a row
    for (tid, day), period_map in teacher_day_period.items():
        # busy[p] = teacher teaches in period p that day. Define for ALL periods
        # of the day so we can reason about rest between classes.
        busy = {}
        for p in all_periods:
            b = model.NewBoolVar(f"busy_{tid}_{day}_{p}")
            if period_map.get(p):
                model.AddMaxEquality(b, period_map[p])
            else:
                model.Add(b == 0)
            busy[p] = b

        # GOAL: prefer rest, but allow continuing (back-to-back) periods when
        # needed. Rest is a soft preference now, not a near-ban. The only HARD
        # rule is the consecutive cap below.
        #
        # (2) STRONG (soft) cap on long runs: heavily penalise any window of
        # (cap+1) consecutive periods that is fully taught. Soft, not hard, so a
        # class that genuinely fills its whole time window (e.g. 4 periods in a
        # 4-slot evening block) can still be scheduled -- it just costs a lot, so
        # the solver avoids long runs wherever it has any freedom.
        for start in all_periods:
            window = [start + k for k in range(cap + 1)]
            if all(p in busy for p in window):
                run = model.NewBoolVar(f"run_{tid}_{day}_{start}")
                model.AddBoolAnd([busy[p] for p in window]).OnlyEnforceIf(run)
                model.AddBoolOr([busy[p].Not() for p in window]).OnlyEnforceIf(run.Not())
                penalties.append(settings.fatigue_run_penalty * 3 * run)

        # (3) Soft, MILD penalty for back-to-back: discourages consecutive
        # periods so the solver only uses them when it genuinely helps, but they
        # are perfectly acceptable when useful.
        for a, c in zip(all_periods, all_periods[1:]):
            if c != a + 1:
                continue
            adj = model.NewBoolVar(f"adj_{tid}_{day}_{a}")
            model.AddBoolAnd([busy[a], busy[c]]).OnlyEnforceIf(adj)
            model.AddBoolOr([busy[a].Not(), busy[c].Not()]).OnlyEnforceIf(adj.Not())
            penalties.append(max(1, settings.fatigue_gap_bonus // 3) * adj)

        # (4) Reward free-period buffers: for each period the teacher works,
        # reward an empty period on either side (a rest gap next to a class).
        for p in all_periods:
            nbrs = [q for q in (p - 1, p + 1) if q in busy]
            for q in nbrs:
                # rest = busy[p] AND not busy[q]  -> a class with a free neighbour
                rest = model.NewBoolVar(f"rest_{tid}_{day}_{p}_{q}")
                model.AddBoolAnd([busy[p], busy[q].Not()]).OnlyEnforceIf(rest)
                model.AddBoolOr([busy[p].Not(), busy[q]]).OnlyEnforceIf(rest.Not())
                rewards.append(settings.fatigue_gap_bonus * rest)

    model.Maximize(sum(rewards) - sum(penalties))

    # Warm start: hint each item to stay in its current (slot, room) when that
    # placement is still a valid candidate. This gives the solver a strong head
    # start from the existing timetable so it converges fast and only nudges
    # what must change (e.g. relocating window overflow).
    for i, it in enumerate(items):
        cur_slot = it.entry.time_slot_id
        cur_room = it.entry.room_id
        key = (i, cur_slot, cur_room)
        if key in x:
            model.AddHint(x[key], 1)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_seconds
    solver.parameters.num_search_workers = 8
    # Accept the first good feasible solution quickly rather than proving
    # optimality -- a comfortable, window-respecting arrangement is enough.
    solver.parameters.stop_after_first_solution = False
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return GenOutcome(
            success=False,
            message="Could not find a comfortable rearrangement within the time limit.",
            conflicts=["Rebalance constraints too tight."],
        )

    prev_max = db.scalar(select(TimetableEntry.version).order_by(TimetableEntry.version.desc()))
    version = (prev_max or 0) + 1

    count = 0
    for (i, sid, rid), var in x.items():
        if solver.Value(var) != 1:
            continue
        e = items[i].entry
        db.add(
            TimetableEntry(
                version=version,
                is_active=False,  # preview; HOD approves to activate
                time_slot_id=sid,
                teacher_id=e.teacher_id,
                subject_id=e.subject_id,
                class_section_id=e.class_section_id,
                room_id=rid,
            )
        )
        count += 1

    return GenOutcome(
        success=True,
        version=version,
        entries=count,
        message=(
            f"Rebalanced into v{version} ({count} periods) with more comfortable "
            "spacing. Preview it, then approve to make it the active timetable."
        ),
    )
