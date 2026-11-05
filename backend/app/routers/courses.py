"""Courses directory: what each teacher teaches, derived from the active timetable.

The HOD may read all teachers' courses; a teacher only gets their own row
(another teacher_id is a 403). Use the
optional ``?teacher_id=`` query parameter to narrow to one teacher. Read-only.
"""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Teacher, TimetableEntry
from app.schemas import CourseOut, CoursesReport, CourseSlot, TeacherCourses
from app.security import forbid, get_current_teacher, is_hod
from app.services.schedule_utils import round_hours, slot_minutes

router = APIRouter(prefix="/api/courses", tags=["courses"])

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


@router.get("", response_model=CoursesReport)
def list_courses(
    teacher_id: int | None = None,
    db: Session = Depends(get_db),
    current: Teacher = Depends(get_current_teacher),
) -> CoursesReport:
    if not is_hod(current):
        if teacher_id not in (None, current.id):
            forbid("You can only view your own courses.")
        teacher_id = current.id
    entries = db.scalars(
        select(TimetableEntry)
        .where(TimetableEntry.is_active == True)  # noqa: E712
        .options(
            joinedload(TimetableEntry.time_slot),
            joinedload(TimetableEntry.subject),
            joinedload(TimetableEntry.class_section),
            joinedload(TimetableEntry.room),
            joinedload(TimetableEntry.teacher),
            joinedload(TimetableEntry.co_teacher),
        )
    ).all()

    ordinals = {
        pi: i + 1
        for i, pi in enumerate(sorted({e.time_slot.period_index for e in entries}))
    }

    q = select(Teacher).where(Teacher.is_active == True)  # noqa: E712
    if teacher_id is not None:
        q = q.where(Teacher.id == teacher_id)
    teachers = sorted(db.scalars(q).all(), key=lambda t: t.name)

    by_teacher: dict[int, list[TimetableEntry]] = defaultdict(list)
    for e in entries:
        by_teacher[e.teacher_id].append(e)
        if e.co_teacher_id and e.co_teacher_id != e.teacher_id:
            by_teacher[e.co_teacher_id].append(e)

    out: list[TeacherCourses] = []
    for t in teachers:
        groups: dict[tuple[int, int], list[TimetableEntry]] = defaultdict(list)
        for e in by_teacher.get(t.id, []):
            groups[(e.subject_id, e.class_section_id)].append(e)

        courses: list[CourseOut] = []
        for rows in groups.values():
            rows.sort(key=lambda e: (e.time_slot.day_of_week, e.time_slot.period_index))
            first = rows[0]
            labs = [e for e in rows if e.is_double]
            lead = any(e.teacher_id == t.id for e in rows)
            co_names = sorted({
                (e.co_teacher.name if e.teacher_id == t.id else e.teacher.name)
                for e in rows
                if (e.teacher_id == t.id and e.co_teacher) or (e.co_teacher_id == t.id)
            })
            lead_name = t.name if lead else (first.teacher.name)

            # Build schedule: merge the two halves of a lab block.
            schedule: list[CourseSlot] = []
            seen_blocks: set[str] = set()
            for e in rows:
                s = e.time_slot
                if e.is_double and e.block_id:
                    if e.block_id in seen_blocks:
                        continue
                    seen_blocks.add(e.block_id)
                    halves = sorted(
                        (r for r in rows if r.block_id == e.block_id),
                        key=lambda r: r.time_slot.period_index,
                    )
                    a, b = halves[0].time_slot, halves[-1].time_slot
                    label = (
                        f"P{ordinals[a.period_index]}–P{ordinals[b.period_index]}"
                        if len(halves) > 1 else f"P{ordinals[a.period_index]}"
                    )
                    schedule.append(CourseSlot(
                        day_of_week=a.day_of_week, day_name=DAY_NAMES[a.day_of_week],
                        period_label=label, start_time=a.start_time, end_time=b.end_time,
                        periods=len(halves), is_lab=True, room=e.room.name,
                    ))
                else:
                    schedule.append(CourseSlot(
                        day_of_week=s.day_of_week, day_name=DAY_NAMES[s.day_of_week],
                        period_label=f"P{ordinals[s.period_index]}",
                        start_time=s.start_time, end_time=s.end_time,
                        periods=1, is_lab=bool(e.is_double), room=e.room.name,
                    ))
            schedule.sort(key=lambda c: (c.day_of_week, c.start_time))

            courses.append(CourseOut(
                subject_id=first.subject_id,
                subject=first.subject.name,
                subject_code=first.subject.code,
                class_section_id=first.class_section_id,
                class_section=first.class_section.name,
                role_in_course="LEAD" if lead else "CO",
                lead_teacher=lead_name,
                co_teachers=co_names,
                periods_per_week=len(rows),
                hours_per_week=round_hours(sum(slot_minutes(e.time_slot) for e in rows)),
                lecture_periods=len(rows) - len(labs),
                lab_periods=len(labs),
                lab_blocks=len({e.block_id or f"e{e.id}" for e in labs}),
                is_lab=bool(labs),
                schedule=schedule,
            ))

        courses.sort(key=lambda c: (c.subject, c.class_section))
        all_rows = by_teacher.get(t.id, [])
        out.append(TeacherCourses(
            teacher_id=t.id,
            name=t.name,
            role=t.role,
            total_courses=len(courses),
            total_periods_per_week=len(all_rows),
            total_hours_per_week=round_hours(sum(slot_minutes(e.time_slot) for e in all_rows)),
            lecture_periods=sum(c.lecture_periods for c in courses),
            lab_periods=sum(c.lab_periods for c in courses),
            courses=courses,
        ))
    return CoursesReport(teachers=out)
