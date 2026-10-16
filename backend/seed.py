"""Seed the database with the real department timetable data.

Run:  .venv\\Scripts\\python.exe seed.py

Logins (password: password123): <firstname>@college.edu
  HOD:      anjana@college.edu
  Teachers: rajeev@college.edu, hari@college.edu, ... etc.

The schedule itself is produced by the OR-Tools generator from the
CourseOfferings defined below (teacher + subject + class + session counts),
balanced to reduce teacher exhaustion. Double sessions = 2-hour lab blocks
that stay glued together.
"""
from __future__ import annotations

from app.database import Base, SessionLocal, engine
from app.models import (
    ClassSection,
    CourseOffering,
    Department,
    Role,
    Room,
    Subject,
    Teacher,
)
from app.security import hash_password

PASSWORD = "password123"

# 8 teaching periods, Mon–Sat. Two breaks (10:20–10:40, 2:20–2:40) are gaps,
# represented by non-adjacent period_index so doubles never cross them.
# period_index: 0,1 | break | 2,3,4,5 | break | 6,7
PERIODS = [
    ("08:30", "09:25"),
    ("09:25", "10:20"),
    ("10:40", "11:35"),
    ("11:35", "12:30"),
    ("12:30", "13:25"),
    ("13:25", "14:20"),
    ("14:40", "15:35"),
    ("15:35", "16:30"),
]
# Mark the slots right after each break boundary so doubles don't span a break:
# we simply never create a double pair across indices (1->2) or (5->6) by
# leaving a period_index gap. To do that we assign indices 0,1,3,4,5,6,8,9.
PERIOD_INDICES = [0, 1, 3, 4, 5, 6, 8, 9]
DAYS = 6  # Mon..Sat


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def run() -> None:
    reset_db()
    db = SessionLocal()
    try:
        # ---------- Departments ----------
        mca = Department(name="Computer Applications")
        bca = Department(name="BCA")
        db.add_all([mca, bca])
        db.flush()
        dept = mca.id

        # ---------- Time slots ----------
        from app.models import TimeSlot
        for day in range(DAYS):
            for ord_i, pidx in enumerate(PERIOD_INDICES):
                start, end = PERIODS[ord_i]
                db.add(TimeSlot(
                    day_of_week=day, period_index=pidx,
                    start_time=start, end_time=end,
                    is_preferred=(ord_i < 4),  # morning-ish preferred
                ))
        db.flush()

        # ---------- Rooms ----------
        admin_lab = Room(name="Admin Lab", is_lab=True, capacity=35)
        digi_lab = Room(name="Digi Lab", is_lab=True, capacity=35)
        # A third lab gives the solver room to place all 28 weekly lab blocks
        # without over-stacking the two named labs in any single slot.
        prog_lab = Room(name="Programming Lab", is_lab=True, capacity=35)
        rooms = [admin_lab, digi_lab, prog_lab]
        for i in range(1, 7):
            rooms.append(Room(name=f"Room {200 + i}", is_lab=False, capacity=60))
        db.add_all(rooms)
        db.flush()

        # ---------- Classes / streams ----------
        # Sem 5 is dropped entirely. Time windows:
        #   AFTERNOON (12:30–4:30): MCA Sem 1 & 3, BCA Sem 3
        #   MORNING   (8:30–12:30): BCA Sem 1 (+ B.Sc Sem 1)
        class_windows = {
            "S1 MCA A": "AFTERNOON",
            "S1 MCA B": "AFTERNOON",
            "S3 MCA": "AFTERNOON",
            "S3 BCA CS": "AFTERNOON",
            "S3 BCA DA": "AFTERNOON",
            "S3 BCA AI": "AFTERNOON",
            "S1 BCA AI A": "MORNING",
            "S1 BCA AI B": "MORNING",
            "S1 BCA CS A": "MORNING",
            "S1 BCA CS B": "MORNING",
            "S1 B.Sc CSIT": "MORNING",
            "S1 B.Sc IT": "MORNING",
        }
        classes = {
            name: ClassSection(name=name, time_window=win)
            for name, win in class_windows.items()
        }
        db.add_all(classes.values())
        db.flush()

        # ---------- Teachers ----------
        def mk(name, email, role=Role.TEACHER, max_day=5):
            t = Teacher(
                name=name, email=email, hashed_password=hash_password(PASSWORD),
                role=role, department_id=dept, max_periods_per_day=max_day,
            )
            db.add(t)
            return t

        T = {}
        T["anjana"] = mk("Anjana", "anjana@college.edu", role=Role.HOD)
        T["rajeev"] = mk("Dr. Rajeev", "rajeev@college.edu")
        T["hari"] = mk("Dr. Hari Narayanan", "hari@college.edu")
        T["spurgen"] = mk("Dr. Spurgen Ratheash", "spurgen@college.edu")
        T["meenu"] = mk("Dr. Meenu Suresh", "meenu@college.edu")
        T["joseph"] = mk("Mr. Joseph James", "joseph@college.edu")
        T["soumya"] = mk("Ms. Soumya K", "soumya@college.edu")
        T["andal"] = mk("Dr. Andal V", "andal@college.edu")
        T["sameeran"] = mk("Mr. Sameeran", "sameeran@college.edu")
        T["sruthi"] = mk("Dr. Sruthi", "sruthi@college.edu")
        T["nisha"] = mk("Dr. Nisha", "nisha@college.edu")
        T["sanjay"] = mk("Mr. Sanjay", "sanjay@college.edu")
        T["vipin"] = mk("Mr. Vipin", "vipin@college.edu")
        T["mani"] = mk("Dr. Manivasagam", "mani@college.edu")
        db.flush()

        # ---------- Subjects (unique code per subject name) ----------
        _subj_cache: dict[str, Subject] = {}

        def subj(name, is_lab=False, importance=1):
            key = name.lower()
            if key in _subj_cache:
                return _subj_cache[key]
            code = "".join(w[0] for w in name.split())[:6].upper() + str(len(_subj_cache) + 1)
            s = Subject(name=name, code=code, department_id=dept, is_lab=is_lab, importance=importance)
            db.add(s)
            db.flush()
            _subj_cache[key] = s
            return s

        # ---------- Course offerings ----------
        # (teacher, subject_name, is_lab_subject, class_name, singles, doubles,
        #  preferred_room, co_teacher, label)
        offerings = []

        def off(teacher, subject_name, class_name, singles=0, doubles=0,
                is_lab=False, room=None, co=None, label=None):
            # Rooms are assigned by the generator (any free lab room for labs),
            # so we don't pin a specific room here — pinning caused clashes when
            # two labs wanted the same named room in one slot.
            s = subj(subject_name, is_lab=is_lab or doubles > 0)
            offerings.append(CourseOffering(
                teacher_id=T[teacher].id,
                co_teacher_id=T[co].id if co else None,
                subject_id=s.id,
                class_section_id=classes[class_name].id,
                room_id=None,
                single_sessions=singles,
                double_sessions=doubles,
                label=label or f"{class_name} · {subject_name}",
            ))

        # Anjana (HOD)
        off("anjana", "BC", "S3 MCA", singles=2, doubles=1, room=digi_lab)
        off("anjana", "ACN", "S1 MCA A", singles=3, doubles=1, room=admin_lab)
        off("anjana", "ACN", "S1 MCA B", singles=2)

        # Rajeev
        off("rajeev", "Python", "S1 MCA A", singles=1, doubles=1, room=digi_lab)
        off("rajeev", "AI IOT", "S3 MCA", singles=2)

        # Hari Narayanan
        off("hari", "DBMS", "S3 BCA CS", singles=4)
        off("hari", "Python", "S3 BCA DA", singles=3, doubles=1, room=admin_lab, co="meenu")
        off("hari", "DL", "S3 MCA", singles=3, doubles=1, room=admin_lab)

        # Spurgen Ratheash
        off("spurgen", "DA Python", "S1 BCA AI B", singles=2, doubles=1, room=admin_lab)
        off("spurgen", "CN", "S3 BCA CS", singles=3)
        off("spurgen", "DSA", "S1 MCA A", singles=3, doubles=1, room=digi_lab)

        # Meenu Suresh
        off("meenu", "CS Python", "S3 BCA CS", singles=3)
        off("meenu", "Gen NOSQL DB", "S3 MCA", singles=2, doubles=1, room=digi_lab)

        # Joseph James
        off("joseph", "ML", "S3 MCA", singles=2, doubles=1, room=digi_lab)
        off("joseph", "Gen SE Python", "S3 BCA AI", singles=4, doubles=1, room=admin_lab, co="soumya")

        # Soumya K
        off("soumya", "AI Digital", "S1 BCA AI A", singles=4, doubles=1, room=admin_lab)
        off("soumya", "DBMS", "S3 BCA AI", singles=3, doubles=1, room=admin_lab, co="joseph")
        off("soumya", "DA OS", "S3 BCA DA", singles=2)

        # Andal V
        off("andal", "Python Theory", "S1 BCA CS A", singles=3, doubles=1, room=digi_lab)
        off("andal", "Python Theory", "S1 BCA CS B", singles=2, doubles=1, room=digi_lab)
        off("andal", "AI", "S1 MCA A", singles=2)

        # Sameeran
        off("sameeran", "Emp Skill", "S1 MCA A", singles=2)
        off("sameeran", "Emp Skill", "S1 MCA B", singles=2)
        off("sameeran", "CN", "S3 BCA AI", singles=3)
        off("sameeran", "AI Literacy", "S1 B.Sc IT", singles=1)

        # Sruthi
        off("sruthi", "Digital", "S1 BCA AI B", singles=4, doubles=1, room=admin_lab)
        off("sruthi", "Digital", "S1 BCA CS A", singles=3, doubles=1, room=digi_lab)
        off("sruthi", "DSM", "S1 BCA CS B", singles=2)
        off("sruthi", "OS", "S3 BCA CS", singles=2)
        off("sruthi", "OS", "S3 BCA AI", singles=2)

        # Nisha
        off("nisha", "DSM", "S1 BCA AI A", singles=2)
        off("nisha", "DSM", "S1 BCA AI B", singles=2)
        off("nisha", "DBMS", "S3 BCA DA", singles=3, doubles=1, room=admin_lab)
        off("nisha", "DSA", "S1 MCA B", singles=3, doubles=1, room=admin_lab)

        # Sanjay
        off("sanjay", "Digital", "S1 B.Sc CSIT", singles=4, doubles=1, room=admin_lab)
        off("sanjay", "Digital", "S1 BCA CS B", singles=3)
        off("sanjay", "AI", "S1 MCA B", singles=3)

        # Vipin — Sem-5 only (dropped). Currently no offerings.

        # Manivasagam
        off("mani", "PFUC", "S1 MCA B", singles=3)
        off("mani", "NLP", "S3 MCA", singles=2, doubles=1, room=digi_lab)
        off("mani", "Python", "S1 MCA B", singles=2, doubles=1, room=digi_lab)

        db.add_all(offerings)
        db.flush()

        # Mark each teacher as qualified for the subjects they teach (and labs
        # co-taught), so the substitution ranker can prefer subject matches.
        for o in offerings:
            t = db.get(Teacher, o.teacher_id)
            s = db.get(Subject, o.subject_id)
            if s not in t.subjects:
                t.subjects.append(s)
            if o.co_teacher_id:
                ct = db.get(Teacher, o.co_teacher_id)
                if s not in ct.subjects:
                    ct.subjects.append(s)

        db.commit()

        total_single = sum(o.single_sessions for o in offerings)
        total_double = sum(o.double_sessions for o in offerings)
        print("Seed complete.")
        print(f"  Teachers: {len(T)}  Classes: {len(classes)}  Offerings: {len(offerings)}")
        print(f"  Weekly periods to place: {total_single} singles + {total_double} lab-blocks "
              f"({total_single + total_double * 2} total period-slots)")
        print("  Login (password123): anjana@college.edu (HOD), rajeev@college.edu, hari@college.edu, ...")
        print("  Now log in as HOD and click Generate & approve to build the balanced timetable.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
