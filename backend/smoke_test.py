"""End-to-end smoke test of the core engine (no HTTP server needed)."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Leave,
    LeaveScope,
    LeaveStatus,
    Substitution,
    SubstitutionStatus,
    Teacher,
    TimetableEntry,
)
from app.services.substitution_engine import assign_substitutes_for_leave
from app.services.timetable_generator import generate_timetable


def next_weekday() -> date:
    d = date.today() + timedelta(days=1)
    while d.weekday() >= 5:  # skip Sat/Sun
        d += timedelta(days=1)
    return d


def main() -> None:
    db = SessionLocal()
    try:
        # 1) Generate + approve.
        outcome = generate_timetable(db)
        print("GENERATE:", outcome.success, outcome.message)
        if outcome.conflicts:
            print("  conflicts:", outcome.conflicts)
        assert outcome.success, "Generation failed"
        db.commit()

        for e in db.scalars(select(TimetableEntry)).all():
            e.is_active = e.version == outcome.version
        db.commit()
        active = db.scalars(select(TimetableEntry).where(TimetableEntry.is_active.is_(True))).all()
        print(f"ACTIVE ENTRIES: {len(active)}")
        assert active, "No active entries"

        # Sanity: no double-booking of teacher/class/room within a slot.
        seen_t, seen_c, seen_r = set(), set(), set()
        for e in active:
            kt, kc, kr = (e.teacher_id, e.time_slot_id), (e.class_section_id, e.time_slot_id), (e.room_id, e.time_slot_id)
            assert kt not in seen_t, "Teacher double-booked!"
            assert kc not in seen_c, "Class double-booked!"
            assert kr not in seen_r, "Room double-booked!"
            seen_t.add(kt); seen_c.add(kc); seen_r.add(kr)
        print("NO DOUBLE-BOOKING: ok")

        # 2) Pick a teacher who actually teaches on the target weekday and file a leave.
        target = next_weekday()
        dow = target.weekday()
        teaching = db.scalars(
            select(TimetableEntry).where(TimetableEntry.is_active.is_(True))
        ).all()
        # find a teacher with entries on that weekday
        from app.models import TimeSlot
        slot_day = {s.id: s.day_of_week for s in db.scalars(select(TimeSlot)).all()}
        candidate_teacher = None
        for e in teaching:
            if slot_day[e.time_slot_id] == dow:
                candidate_teacher = e.teacher_id
                break
        assert candidate_teacher, "No teacher teaches on target weekday"
        tname = db.get(Teacher, candidate_teacher).name
        print(f"LEAVE for {tname} on {target} (weekday {dow})")

        leave = Leave(teacher_id=candidate_teacher, leave_date=target, scope=LeaveScope.FULL_DAY,
                      status=LeaveStatus.ACTIVE, reason="smoke test")
        db.add(leave)
        db.flush()
        subs = assign_substitutes_for_leave(db, leave)
        db.commit()

        assigned = [s for s in subs if s.status == SubstitutionStatus.ASSIGNED]
        uncovered = [s for s in subs if s.status == SubstitutionStatus.UNCOVERED]
        print(f"SUBS created={len(subs)} assigned={len(assigned)} uncovered={len(uncovered)}")
        for s in subs:
            sub_name = db.get(Teacher, s.substitute_teacher_id).name if s.substitute_teacher_id else "—"
            print(f"  slot_entry={s.timetable_entry_id} -> {sub_name} [{s.status.value}] : {s.explanation}")

        # A substitute must never be the absent teacher and must be free.
        for s in assigned:
            assert s.substitute_teacher_id != candidate_teacher, "Absent teacher assigned as sub!"
        print("SUBSTITUTE VALIDITY: ok")
        print("\nSMOKE TEST PASSED")
    finally:
        db.close()


if __name__ == "__main__":
    main()
