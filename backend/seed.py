"""Seed the database with realistic sample data.

Run:  .venv\\Scripts\\python.exe seed.py

Logins (password is the same for everyone): password123
  HOD:      hod@college.edu
  Teachers: <first name lowercase>@college.edu  e.g. asha@college.edu
"""
from __future__ import annotations

from app.database import Base, SessionLocal, engine
from app.models import (
    Availability,
    ClassSection,
    Department,
    Role,
    Room,
    Subject,
    Teacher,
    TimeSlot,
)
from app.security import hash_password

PASSWORD = "password123"

# 5 periods/day, Monday..Friday. Periods 1 and 2 are "preferred" (morning).
DAYS = 5
PERIODS = [
    ("09:00", "09:50", True),
    ("10:00", "10:50", True),
    ("11:00", "11:50", False),
    ("12:00", "12:50", False),
    ("14:00", "14:50", False),
]


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def run() -> None:
    reset_db()
    db = SessionLocal()
    try:
        # Departments
        cse = Department(name="Computer Science")
        ece = Department(name="Electronics")
        db.add_all([cse, ece])
        db.flush()

        # Time slots
        slots: list[TimeSlot] = []
        for day in range(DAYS):
            for idx, (start, end, pref) in enumerate(PERIODS):
                s = TimeSlot(day_of_week=day, period_index=idx, start_time=start, end_time=end, is_preferred=pref)
                slots.append(s)
                db.add(s)
        db.flush()

        # Rooms
        r101 = Room(name="R-101", is_lab=False, capacity=60)
        r102 = Room(name="R-102", is_lab=False, capacity=60)
        r103 = Room(name="R-103", is_lab=False, capacity=60)
        lab1 = Room(name="LAB-1", is_lab=True, capacity=30)
        lab2 = Room(name="LAB-2", is_lab=True, capacity=30)
        db.add_all([r101, r102, r103, lab1, lab2])
        db.flush()

        # Subjects (kept small so a feasible timetable exists quickly)
        maths = Subject(name="Mathematics", code="MA101", department_id=cse.id, importance=3, is_lab=False, periods_per_week=2)
        dsa = Subject(name="Data Structures", code="CS201", department_id=cse.id, importance=3, is_lab=False, periods_per_week=2)
        dbms = Subject(name="Databases", code="CS202", department_id=cse.id, importance=2, is_lab=False, periods_per_week=1)
        cslab = Subject(name="Programming Lab", code="CS2L", department_id=cse.id, importance=2, is_lab=True, periods_per_week=1)
        signals = Subject(name="Signals & Systems", code="EC201", department_id=ece.id, importance=2, is_lab=False, periods_per_week=1)
        eclab = Subject(name="Electronics Lab", code="EC2L", department_id=ece.id, importance=2, is_lab=True, periods_per_week=1)
        db.add_all([maths, dsa, dbms, cslab, signals, eclab])
        db.flush()

        # Classes
        c3a = ClassSection(name="CSE-3A")
        c3b = ClassSection(name="CSE-3B")
        db.add_all([c3a, c3b])
        db.flush()

        # Teachers (HOD + faculty). subjects assigned for qualification.
        def make(name: str, email: str, dept: Department, role: Role = Role.TEACHER, subs=None, max_day=5):
            t = Teacher(
                name=name,
                email=email,
                hashed_password=hash_password(PASSWORD),
                role=role,
                department_id=dept.id,
                max_periods_per_day=max_day,
            )
            if subs:
                t.subjects = subs
            db.add(t)
            return t

        hod = make("Dr. Rao (HOD)", "hod@college.edu", cse, role=Role.HOD, subs=[maths, dsa])
        asha = make("Asha Menon", "asha@college.edu", cse, subs=[maths, dsa, dbms])
        bala = make("Bala Krishnan", "bala@college.edu", cse, subs=[dsa, dbms, cslab])
        chitra = make("Chitra Nair", "chitra@college.edu", cse, subs=[maths, dbms, cslab])
        deepak = make("Deepak Varma", "deepak@college.edu", ece, subs=[signals, eclab])
        esha = make("Esha Pillai", "esha@college.edu", ece, subs=[signals, eclab, maths])
        db.flush()

        # Everyone available all slots (no Availability rows = available everywhere).
        # Give one teacher a restricted availability to exercise the constraint:
        # Bala is unavailable on the last period each day.
        last_period_slots = [s for s in slots if s.period_index == len(PERIODS) - 1]
        available_for_bala = [s for s in slots if s.period_index != len(PERIODS) - 1]
        for s in available_for_bala:
            db.add(Availability(teacher_id=bala.id, time_slot_id=s.id))

        db.commit()

        print("Seed complete.")
        print(f"  Departments: 2, Slots: {len(slots)}, Rooms: 5, Subjects: 6, Classes: 2, Teachers: 6")
        print("  Login (password123): hod@college.edu | asha@college.edu | bala@college.edu | ...")
    finally:
        db.close()


if __name__ == "__main__":
    run()
