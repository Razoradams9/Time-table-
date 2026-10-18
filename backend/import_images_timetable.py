"""Import the full department timetable transcribed from the 14 teacher grids.

Run:  .venv\\Scripts\\python.exe import_images_timetable.py

This is a FAITHFUL transcription of every cell in the 14 teacher photos
(Anjana, Rajeev, Hari, Spurgen, Meenu, Joseph, Soumya, Andal, Sameeran,
Sruthi, Nisha, Sanjay, Vipin, Manivasagam). It:

  * Ensures all 14 teachers exist (matching the current DB).
  * Creates every class, subject, and room the grids reference (incl. S5 BCA,
    B.Sc CSIT/IT, and the Digital Lab) if missing.
  * Inserts every period at EXACTLY the day/period shown in the image.
  * Merges co-taught labs (e.g. "Meenu & Hari", "Joseph & Soumya") into ONE
    entry with a co_teacher so it appears on both teachers' timetables.
  * Marks the imported version active so it shows across the app.

Day/period index mapping (matches the grid columns & the backend seed):
  days:    0=Mon 1=Tue 2=Wed 3=Thu 4=Fri 5=Sat
  periods: 0=08:30 1=09:25 | break | 2=10:40 3=11:35 4=12:30 5=13:25 | break |
           6=14:40 7=15:35
  (period_index values in TimeSlot are 0,1,3,4,5,6,8,9 — we map the ordinal
   column 0..7 to those actual indices.)

Each schedule row is a dict so co-taught labs and double (lab) blocks are
explicit:
  {"d":, "p":, "cls":, "subj":, "lab":<room hint or None>,
   "co":<co-teacher key or None>, "double":<True for a 2-period lab block>}
Only the PRIMARY teacher lists a shared co-taught lab; the co-teacher is wired
in automatically so it is not duplicated.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import (
    ClassSection,
    Department,
    Role,
    Room,
    Subject,
    Teacher,
    TimeSlot,
    TimetableEntry,
)
from app.security import hash_password

PASSWORD = "password123"
MON, TUE, WED, THU, FRI, SAT = range(6)

# Map grid column ordinal (0..7) -> actual TimeSlot.period_index used in seed.
COL_TO_PIDX = [0, 1, 3, 4, 5, 6, 8, 9]

# ---------------------------------------------------------------------------
# Teachers (key -> (display name, email, role)). Matches the current DB.
# ---------------------------------------------------------------------------
TEACHERS = {
    "anjana":   ("Anjana", "anjana@college.edu", Role.HOD),
    "rajeev":   ("Dr. Rajeev", "rajeev@college.edu", Role.TEACHER),
    "hari":     ("Dr. Hari Narayanan", "hari@college.edu", Role.TEACHER),
    "spurgen":  ("Dr. Spurgen Ratheash", "spurgen@college.edu", Role.TEACHER),
    "meenu":    ("Dr. Meenu Suresh", "meenu@college.edu", Role.TEACHER),
    "joseph":   ("Mr. Joseph James", "joseph@college.edu", Role.TEACHER),
    "soumya":   ("Ms. Soumya K", "soumya@college.edu", Role.TEACHER),
    "andal":    ("Dr. Andal V", "andal@college.edu", Role.TEACHER),
    "sameeran": ("Mr. Sameeran", "sameeran@college.edu", Role.TEACHER),
    "sruthi":   ("Dr. Sruthi", "sruthi@college.edu", Role.TEACHER),
    "nisha":    ("Dr. Nisha", "nisha@college.edu", Role.TEACHER),
    "sanjay":   ("Mr. Sanjay", "sanjay@college.edu", Role.TEACHER),
    "vipin":    ("Mr. Vipin", "vipin@college.edu", Role.TEACHER),
    "mani":     ("Dr. Manivasagam", "mani@college.edu", Role.TEACHER),
}

# Lab room hints in the grids map to these rooms.
ROOM_HINTS = {"ADMIN": "Admin Lab", "DIGI": "Digi Lab", "DIGITAL": "Digital Lab"}


def P(d, p, cls, subj, lab=None, co=None, double=False):
    return {"d": d, "p": p, "cls": cls, "subj": subj, "lab": lab, "co": co, "double": double}


# ---------------------------------------------------------------------------
# Faithful transcription of all 14 grids.
# ---------------------------------------------------------------------------
SCHEDULE: dict[str, list[dict]] = {
    # ===== Mrs. ANJANA (HOD) =====
    "anjana": [
        P(MON, 5, "S1 MCA A", "ACN"),        # moved c4->c5 (Spurgen DSA owns c4); item 2
        P(MON, 6, "S1 MCA B", "ACN"),
        P(TUE, 5, "S1 MCA A", "ACN"),        # moved Mon c7->Tue c5 (Andal AI owns Mon c7); item 7
        P(TUE, 4, "S1 MCA B", "ACN"),
        P(WED, 4, "S3 MCA CS", "BC"),
        P(THU, 4, "S3 MCA CS", "BC"),        # moved Wed c6->Thu c4 (Hari DL Lab owns Wed c6-c7); item 1
        P(THU, 5, "S3 MCA CS", "BC Lab", lab="DIGI"),  # moved Wed c7->Thu c5; single-period lab; item 1
        P(THU, 6, "S1 MCA A", "ACN Lab", lab="ADMIN"),  # moved Thu c4->c6 (Spurgen DSA owns Thu c4); item 2
        P(FRI, 6, "S1 MCA A", "ACN Lab", lab="ADMIN", double=True),  # Fri c4-c5 double -> c6-c7 (Spurgen DSA Lab owns Fri c4); items 2,12
        P(SAT, 0, "S1 MCA A", "ACN Lab", lab="ADMIN", double=True),  # Sat c4-c5 double -> c0-c1 (Andal AI owns Sat c4, no free afternoon pair); item 7
        P(SAT, 6, "S3 MCA CS", "BC"),
    ],
    # ===== Dr. RAJEEV =====
    "rajeev": [
        P(MON, 0, "S5 BCA AI", "DL"),
        P(MON, 1, "S5 BCA AI", "DL"),
        P(MON, 2, "S5 BCA AI", "ML Lab", lab="ADMIN", co="joseph", double=True),
        P(MON, 6, "S3 MCA GEN", "AI IOT"),   # moved c5->c6 (Mani NLP Lab owns c4-c5); item 24
        P(TUE, 1, "S5 BCA AI", "DL"),
        P(TUE, 6, "S1 MCA A", "Python"),
        P(TUE, 7, "S3 MCA GEN", "AI IOT"),
        P(WED, 1, "S5 BCA AI", "DL"),
        P(WED, 3, "S1 MCA A", "Python"),
        P(WED, 4, "S1 MCA A", "Python Lab", lab="DIGI", double=True),
        P(THU, 0, "S5 BCA AI", "DL Lab", lab="ADMIN", co="joseph", double=True),
        P(SAT, 6, "S3 MCA GEN", "AI IOT"),   # moved c3->c6 (Meenu NOSQL owns c3; coord w/ item 26); item 4
        P(SAT, 7, "S1 MCA A", "Python"),
    ],
    # ===== Dr. HARI NARAYANAN =====
    "hari": [
        P(MON, 4, "S3 BCA CS", "Python Lab", lab="ADMIN", co="meenu", double=True),
        P(MON, 7, "S3 MCA CS", "AI DL"),
        P(TUE, 4, "S3 BCA CS", "DBMS"),
        P(TUE, 5, "S3 BCA DA", "Python"),
        P(TUE, 6, "S3 BCA DA", "Python Lab", lab="ADMIN", double=True),
        P(WED, 5, "S3 MCA CS", "AI DL"),
        P(WED, 6, "S3 MCA CS", "DL Lab", lab="ADMIN", double=True),
        P(THU, 4, "S3 BCA CS", "DBMS"),
        P(THU, 5, "S3 BCA DA", "Python"),
        P(FRI, 4, "S3 MCA CS", "AI DL"),
        P(FRI, 5, "S3 BCA CS", "DBMS Lab", lab="ADMIN", co="meenu", double=True),
        P(SAT, 4, "S3 BCA CS", "DBMS"),
        P(SAT, 6, "S3 BCA DA", "Python"),
    ],
    # ===== Dr. SPURGEN RATHEASH =====
    "spurgen": [
        P(MON, 0, "S5 BCA DA+Gen", "DWDM"),
        P(MON, 3, "S1 BCA AI-B", "DA Python"),
        P(MON, 4, "S1 MCA A", "DSA"),
        P(MON, 6, "S3 BCA CS", "CN"),
        P(MON, 7, "S3 BCA CS", "CN"),
        P(TUE, 0, "S1 BCA AI-B", "DA Python Lab", lab="ADMIN", double=True),
        P(TUE, 6, "S3 BCA CS", "CN"),
        P(TUE, 7, "S3 BCA CS", "CN"),
        P(WED, 0, "S5 BCA DA+Gen", "DWDM"),
        P(WED, 2, "S5 BCA DA+Gen", "DWDM Lab", lab="DIGI", double=True),
        P(WED, 4, "S3 BCA CS", "CN"),
        P(WED, 6, "S1 MCA A", "DSA Lab", lab="DIGI", double=True),
        P(THU, 4, "S1 MCA A", "DSA"),
        P(FRI, 1, "S5 BCA DA+Gen", "DWDM"),
        P(FRI, 3, "S1 BCA AI-B", "DA Python"),
        P(FRI, 4, "S1 MCA A", "DSA Lab"),
        P(SAT, 0, "S1 BCA AI-B", "DA Python"),
        P(SAT, 3, "S1 MCA A", "DSA"),
    ],
    # ===== Dr. MEENU SURESH =====
    "meenu": [
        P(MON, 1, "S5 BCA DA+Gen", "R Prog"),
        P(MON, 2, "S5 BCA DA+Gen", "R Prog Lab", lab="ADMIN", double=True),
        # co-taught Python Lab with Hari (listed on Hari as primary) -> not duplicated
        P(MON, 7, "S3 MCA GEN", "NOSQL DB"),
        P(TUE, 5, "S3 BCA CS", "Python"),    # moved c4->c5 (Hari DBMS owns Tue c4); item 3
        P(WED, 5, "S3 BCA CS", "Python"),    # moved c4->c5 (Spurgen CN owns Wed c4); item 3
        P(WED, 6, "S3 MCA GEN", "NOSQL DB"),  # moved c5->c6 (Mani Python owns Wed c5); item 25
        P(THU, 0, "S5 BCA DA+Gen", "R Prog"),
        P(THU, 5, "S3 MCA GEN", "NOSQL DB Lab", lab="DIGI", double=True),
        P(SAT, 3, "S3 MCA GEN", "NOSQL DB"),
        P(SAT, 6, "S3 BCA CS", "Python"),
    ],
    # ===== Mr. JOSEPH JAMES =====
    "joseph": [
        # Mon P2 ML Lab (co-taught with Rajeev) is listed on Rajeev as primary.
        P(MON, 5, "S3 MCA CS", "ML"),
        P(MON, 6, "S3 BCA AI", "Python Lab", lab="ADMIN", co="soumya", double=True),
        P(TUE, 4, "S3 BCA AI", "DBMS Lab", lab="ADMIN", co="soumya", double=True),
        P(TUE, 6, "S3 MCA CS", "ML Lab", lab="DIGITAL", double=True),
        P(WED, 0, "S5 BCA AI", "ML"),
        P(WED, 2, "S5 BCA AI", "ML"),
        P(WED, 4, "S3 MCA GEN", "SE"),
        P(WED, 6, "S3 BCA AI", "Python"),    # moved c5->c6 (Sameeran CN owns Wed c5); item 11
        # Thu P0 DL Lab (co-taught with Rajeev) is listed on Rajeev as primary.
        P(THU, 5, "S3 BCA AI", "Python"),
        P(FRI, 6, "S3 MCA CS", "ML"),        # moved c4->c6 (Hari AI DL owns Fri c4, SE owns c5); item 5
        P(FRI, 5, "S3 MCA GEN", "SE"),
        P(SAT, 4, "S3 MCA CS", "ML"),
        P(SAT, 7, "S3 MCA GEN", "SE"),       # moved c5->c7 (Mani Python owns Sat c5); item 26
        P(SAT, 5, "S3 BCA AI", "Python"),    # moved c6->c5 (Sameeran GE owns Sat c6); item 13
    ],
    # ===== Ms. SOUMYA K =====
    "soumya": [
        P(MON, 0, "S1 BCA AI-A", "AI Digital Lab", lab="ADMIN", double=True),
        # Mon P6 "S3 BCA AI Python Joseph & Soumya" co-taught lab -> on Joseph (primary).
        P(TUE, 0, "S1 BCA AI-A", "AI Digital"),
        # Tue DBMS Lab (co-taught with Joseph) -> on Joseph (primary).
        P(TUE, 6, "S3 BCA AI", "DBMS"),
        P(WED, 0, "S5 BCA CS", "Crypto"),
        P(WED, 6, "S3 BCA DA", "OS"),
        P(THU, 0, "S1 BCA AI-A", "AI Digital"),
        P(THU, 2, "S5 BCA CS", "Crypto"),    # moved c1->c2 (Andal Pentest owns Thu c1); item 8
        P(THU, 6, "S3 BCA DA", "OS"),        # moved c5->c6 (Hari Python owns Thu c5); item 6
        P(FRI, 1, "S5 BCA CS", "Crypto"),
        P(FRI, 4, "S3 BCA AI", "DBMS"),
        P(FRI, 5, "S3 BCA DA", "OS"),
        P(SAT, 0, "S1 BCA AI-A", "AI Digital"),
        P(SAT, 4, "S3 BCA AI", "DBMS"),
    ],
    # ===== Dr. ANDAL V =====
    "andal": [
        P(MON, 1, "S5 BCA CS", "Pentest Lab", lab="DIGI", double=True),
        P(MON, 3, "S1 BCA CS-A", "Python Lab", lab="DIGITAL", double=True),
        P(MON, 7, "S1 MCA A", "AI"),
        P(TUE, 1, "S5 BCA CS", "Pentest"),
        P(WED, 0, "S1 BCA CS-B", "Python Lab", lab="DIGI", double=True),
        P(THU, 1, "S5 BCA CS", "Pentest"),
        P(THU, 2, "S1 BCA CS-A", "Python Theory"),
        P(THU, 5, "S1 MCA A", "AI"),
        P(FRI, 3, "S1 BCA CS-A", "Python Theory"),
        P(FRI, 4, "S1 BCA CS-B", "Python Theory"),
        P(SAT, 1, "S5 BCA CS", "Pentest"),
        P(SAT, 2, "S1 BCA CS-A", "Python Theory"),
        P(SAT, 0, "S1 BCA CS-A", "Python Theory"),  # moved c3->c0 (Sruthi Digital owns Sat c3); item 16
        P(SAT, 4, "S1 MCA A", "AI"),
    ],
    # ===== Mr. SAMEERAN =====
    "sameeran": [
        P(FRI, 2, "S5 BCA AI", "Gen AI"),    # moved Mon c3->Fri c2 (Rajeev ML Lab owns Mon c2-c3); item 9
        P(MON, 5, "S3 BCA AI", "CN"),
        P(TUE, 0, "S5 BCA AI", "Gen AI"),
        P(TUE, 3, "S1 MCA A", "Emp Skill"),
        P(SAT, 1, "S5 BCA AI", "Gen AI"),    # moved Wed c1->Sat c1 (Rajeev DL owns Wed c1); item 10
        P(WED, 3, "S1 MCA B", "Emp Skill"),
        P(WED, 5, "S3 BCA AI", "CN"),
        P(THU, 1, "S1 B.Sc IT", "AI Literacy"),
        P(THU, 2, "S5 BCA AI", "GE"),
        P(THU, 3, "S5 BCA AI", "GE"),
        P(THU, 6, "S3 BCA AI", "GE"),
        P(THU, 7, "S3 BCA AI", "GE"),
        P(FRI, 3, "S5 BCA AI", "GE"),
        P(FRI, 5, "S1 MCA A", "Emp Skill"),
        P(SAT, 6, "S3 BCA AI", "GE"),
    ],
    # ===== Dr. SRUTHI =====
    "sruthi": [
        P(MON, 0, "S1 BCA AI-B", "Digital Lab", lab="ADMIN", double=True),
        P(MON, 2, "S3 BCA CS", "DSM"),
        P(MON, 4, "S3 BCA AI", "OS"),        # moved c5->c4 (Sameeran CN owns Mon c5); item 14
        P(THU, 6, "S3 BCA CS", "OS"),        # moved Mon c6->Thu c6 (Spurgen CN owns Mon c6); item 15
        P(TUE, 0, "S1 BCA CS-A", "Digital Lab", lab="DIGI", double=True),
        P(WED, 3, "S1 BCA AI-B", "Digital"),
        P(WED, 6, "S3 BCA CS", "OS"),
        P(WED, 7, "S3 BCA AI", "OS"),
        P(THU, 0, "S1 BCA CS-A", "Digital"),
        P(THU, 5, "S3 BCA CS", "OS"),
        P(FRI, 0, "S1 BCA AI-B", "Digital"),
        P(FRI, 2, "S1 BCA CS-B", "DSM"),
        P(FRI, 5, "S3 BCA AI", "OS"),
        P(SAT, 3, "S1 BCA CS-A", "Digital"),
        P(SAT, 4, "S1 BCA AI-B", "Digital"),
    ],
    # ===== Dr. NISHA =====
    "nisha": [
        P(SAT, 2, "S5 BCA AI", "NLP"),       # moved Mon c1->Sat c2 (Rajeev DL owns Mon c1); item 17
        P(MON, 4, "S3 BCA DA", "DBMS"),
        P(MON, 5, "S1 MCA B", "DSA"),
        P(TUE, 2, "S5 BCA AI", "NLP"),
        P(TUE, 4, "S3 BCA DA", "DBMS"),
        P(WED, 2, "S1 BCA AI-B", "DSM"),
        P(WED, 4, "S3 BCA DA", "DBMS Lab", lab="ADMIN", double=True),
        P(THU, 1, "S1 BCA AI-A", "DSM"),
        P(FRI, 1, "S5 BCA AI", "NLP"),
        P(FRI, 2, "S1 BCA AI-B", "DSM"),     # moved c3->c2 (Spurgen DA Python owns Fri c3); item 18
        P(FRI, 4, "S1 MCA B", "DSA"),
        P(FRI, 5, "S1 MCA B", "DSA Lab", lab="ADMIN", double=True),
        P(SAT, 3, "S1 MCA B", "DSA Lab", lab="ADMIN", double=True),
        P(SAT, 5, "S3 BCA DA", "DBMS"),
        P(SAT, 7, "S1 MCA B", "DSA"),
    ],
    # ===== Mr. SANJAY =====
    "sanjay": [
        P(MON, 0, "S1 B.Sc CSIT", "Digital"),
        P(MON, 1, "S1 BCA CS-B", "Digital"),
        P(MON, 4, "S5 BCA DA+Gen", "CLDA"),
        P(WED, 4, "S1 MCA B", "AI"),         # moved Mon c5->Wed c4 (Nisha DSA owns Mon c5); item 19b
        P(TUE, 0, "S5 BCA DA+Gen", "CLDA"),
        P(TUE, 1, "S1 BCA CS-B", "Digital"),
        P(TUE, 5, "S1 MCA B", "AI"),
        P(WED, 1, "S5 BCA DA+Gen", "CLDA"),  # moved c2->c1 (Spurgen DWDM Lab owns Wed c2-c3); item 21
        P(THU, 0, "S1 BCA CS-B", "Digital Lab"),
        P(THU, 3, "S1 B.Sc CSIT", "Digital Lab", lab="ADMIN", double=True),
        P(THU, 7, "S1 MCA B", "AI"),         # moved c4->c7 (own Digital Lab double owns Thu c3-c4, Mani lab Thu c5-c6); item 22
        P(FRI, 0, "S1 B.Sc CSIT", "Digital"),
        P(SAT, 0, "S1 BCA CS-B", "Digital"),
        P(SAT, 2, "S1 B.Sc CSIT", "Digital"),
    ],
    # ===== Mr. VIPIN =====
    "vipin": [
        P(MON, 0, "S5 BCA CS", "DF"),        # moved c2->c0 (Andal Pentest Lab owns Mon c1-c2); item 23
        P(MON, 3, "S5 BCA CS", "DF"),
        P(MON, 4, "S5 BCA CS", "CF"),
        P(MON, 7, "S5 BCA CS", "Cyber Lab", lab="DIGITAL"),  # last slot: single-period lab
        P(TUE, 2, "S5 BCA CS", "Digital Forensics Lab", lab="DIGI", double=True),
        P(TUE, 5, "S5 BCA CS", "CF"),
        P(WED, 2, "S5 BCA CS", "DF"),
        P(SAT, 5, "S5 BCA CS", "CF"),
    ],
    # ===== Dr. MANIVASAGAM =====
    "mani": [
        P(MON, 4, "S3 MCA GEN", "NLP Lab", lab="DIGI", double=True),
        P(THU, 5, "S1 MCA B", "Python Lab", lab="DIGI", double=True),  # moved Mon c5-c6->Thu c5-c6 (Nisha DSA owns Mon c5, Anjana ACN Mon c6); item 19c
        P(MON, 7, "S1 MCA B", "Python"),
        P(TUE, 1, "S1 MCA B", "PFUC"),
        P(TUE, 5, "S3 MCA GEN", "NLP"),
        P(TUE, 6, "S3 MCA GEN", "NLP"),
        P(WED, 5, "S3 MCA GEN", "Python"),
        P(THU, 1, "S1 MCA B", "PFUC"),
        P(THU, 3, "S3 MCA GEN", "Python Lab", lab="DIGI", double=True),
        P(FRI, 3, "S3 MCA GEN", "C Lab", lab="ADMIN"),
        P(FRI, 4, "S3 MCA GEN", "NLP Lab", lab="DIGI"),
        P(SAT, 1, "S1 MCA B", "PFUC"),
        P(SAT, 4, "S3 MCA GEN", "NLP Lab", lab="DIGI"),
        P(SAT, 5, "S3 MCA GEN", "Python"),
    ],
}


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # ---- Department ----
        dept = db.scalar(select(Department).where(Department.name == "Computer Applications"))
        if dept is None:
            dept = Department(name="Computer Applications")
            db.add(dept)
            db.flush()

        # ---- Teachers (ensure all exist) ----
        tcache: dict[str, Teacher] = {}
        for key, (name, email, role) in TEACHERS.items():
            t = db.scalar(select(Teacher).where(Teacher.email == email))
            if t is None:
                t = Teacher(
                    name=name, email=email, hashed_password=hash_password(PASSWORD),
                    role=role, department_id=dept.id, max_periods_per_day=8,
                )
                db.add(t)
                db.flush()
            else:
                # keep teachers active & roomy enough for their real load
                t.is_active = True
                if t.max_periods_per_day < 8:
                    t.max_periods_per_day = 8
            tcache[key] = t

        # ---- Rooms (ensure lab + lecture rooms exist) ----
        def ensure_room(name: str, is_lab: bool) -> Room:
            r = db.scalar(select(Room).where(Room.name == name))
            if r is None:
                r = Room(name=name, is_lab=is_lab, capacity=35 if is_lab else 60)
                db.add(r)
                db.flush()
            return r

        admin = ensure_room("Admin Lab", True)
        digi = ensure_room("Digi Lab", True)
        digital = ensure_room("Digital Lab", True)
        ensure_room("Programming Lab", True)
        lecture_rooms = [ensure_room(f"Room {200 + i}", False) for i in range(1, 9)]
        lab_by_hint = {"ADMIN": admin, "DIGI": digi, "DIGITAL": digital}
        any_lab = [admin, digi, digital]

        # ---- Classes (create every class referenced) ----
        all_classes = sorted({row["cls"] for rows in SCHEDULE.values() for row in rows})

        def window_for(cls: str) -> str:
            # S1 & S5 BCA run mornings; S3 (any) and all MCA run afternoons.
            if "MCA" in cls:
                return "AFTERNOON"
            if cls.startswith("S3"):
                return "AFTERNOON"
            if cls.startswith(("S1", "S5")):
                return "MORNING"
            return "ANY"

        ccache: dict[str, ClassSection] = {}
        for cname in all_classes:
            c = db.scalar(select(ClassSection).where(ClassSection.name == cname))
            if c is None:
                c = ClassSection(name=cname, time_window=window_for(cname))
                db.add(c)
                db.flush()
            ccache[cname] = c

        # ---- Subjects (create by name; stable unique code) ----
        scache: dict[str, Subject] = {}

        def ensure_subject(name: str) -> Subject:
            key = name.lower()
            if key in scache:
                return scache[key]
            s = db.scalar(select(Subject).where(Subject.name == name))
            if s is None:
                base = "".join(w[0] for w in name.split() if w)[:6].upper() or "SUBJ"
                code = f"{base}{len(scache) + 1}"
                is_lab = name.lower().endswith("lab")
                s = Subject(name=name, code=code, department_id=dept.id, is_lab=is_lab)
                db.add(s)
                db.flush()
            scache[key] = s
            return s

        # ---- Wipe existing timetable, pick a fresh active version ----
        existing = db.scalars(select(TimetableEntry.version)).all()
        version = (max(existing) + 1) if existing else 1
        db.query(TimetableEntry).delete()
        db.flush()

        # ---- Occupancy trackers to catch clashes (report, don't silently drop) ----
        teacher_busy: dict[tuple, str] = {}
        class_busy: dict[tuple, str] = {}
        room_busy: dict[tuple, int] = {}
        conflicts: list[str] = []
        counts: dict[str, int] = defaultdict(int)
        entries: list[TimetableEntry] = []

        def pick_room(pidx_list: list[int], day: int, lab_hint, is_lab: bool) -> Room:
            # Prefer the named lab if free across all needed slots; else any lab;
            # else a free lecture room. Falls back to the first candidate.
            def slot_ids(room: Room):
                return [(day, p, room.id) for p in pidx_list]

            candidates: list[Room] = []
            if lab_hint and lab_hint in lab_by_hint:
                candidates.append(lab_by_hint[lab_hint])
            if is_lab or lab_hint:
                candidates += [r for r in any_lab if r not in candidates]
            else:
                candidates += lecture_rooms
            for r in candidates:
                if all((day, p, r.id) not in room_busy for p in pidx_list):
                    return r
            # overflow: try the other pool
            overflow = lecture_rooms if (is_lab or lab_hint) else any_lab
            for r in overflow:
                if all((day, p, r.id) not in room_busy for p in pidx_list):
                    return r
            return candidates[0] if candidates else lecture_rooms[0]

        import uuid

        for key, rows in SCHEDULE.items():
            teacher = tcache[key]
            for row in rows:
                day = row["d"]
                col = row["p"]
                cls = ccache[row["cls"]]
                subject = ensure_subject(row["subj"])
                co = tcache[row["co"]] if row["co"] else None
                is_double = bool(row["double"])

                # Columns occupied: a double takes this ordinal + next ordinal.
                cols = [col, col + 1] if is_double else [col]
                if is_double and col + 1 > 7:
                    conflicts.append(f"{teacher.name}: double at col {col} overflows the day; placed single.")
                    cols = [col]
                    is_double = False
                pidxs = [COL_TO_PIDX[c] for c in cols]

                # clash checks
                clash = False
                for pidx in pidxs:
                    slotkey_t = (day, pidx, teacher.id)
                    slotkey_c = (day, pidx, cls.id)
                    if slotkey_t in teacher_busy:
                        conflicts.append(
                            f"{teacher.name} double-booked d{day} p{pidx}: "
                            f"'{teacher_busy[slotkey_t]}' vs '{row['cls']} {row['subj']}'")
                        clash = True
                    if co and (day, pidx, co.id) in teacher_busy:
                        conflicts.append(
                            f"{co.name} (co) double-booked d{day} p{pidx} for {row['cls']} {row['subj']}")
                        clash = True
                    if slotkey_c in class_busy:
                        conflicts.append(
                            f"{row['cls']} double-booked d{day} p{pidx}: "
                            f"'{class_busy[slotkey_c]}' vs '{teacher.name} {row['subj']}'")
                        clash = True
                if clash:
                    continue

                room = pick_room(pidxs, day, row["lab"], subject.is_lab)
                block = uuid.uuid4().hex[:12] if is_double else None

                for pidx in pidxs:
                    slot = db.scalar(select(TimeSlot).where(
                        TimeSlot.day_of_week == day, TimeSlot.period_index == pidx))
                    if slot is None:
                        conflicts.append(f"No TimeSlot for d{day} p{pidx} ({row['cls']} {row['subj']})")
                        continue
                    teacher_busy[(day, pidx, teacher.id)] = f"{row['cls']} {row['subj']}"
                    class_busy[(day, pidx, cls.id)] = f"{teacher.name} {row['subj']}"
                    if co:
                        teacher_busy[(day, pidx, co.id)] = f"{row['cls']} {row['subj']} (co)"
                    room_busy[(day, pidx, room.id)] = slot.id
                    entries.append(TimetableEntry(
                        version=version, is_active=False, time_slot_id=slot.id,
                        teacher_id=teacher.id, co_teacher_id=co.id if co else None,
                        subject_id=subject.id, class_section_id=cls.id,
                        room_id=room.id, block_id=block, is_double=is_double,
                    ))
                    counts[key] += 1
                    if co:
                        counts[row["co"]] += 1

        # Mark subject qualifications so substitution ranking has something to use.
        for e in entries:
            s = db.get(Subject, e.subject_id)
            for tid in (e.teacher_id, e.co_teacher_id):
                if not tid:
                    continue
                t = db.get(Teacher, tid)
                if s not in t.subjects:
                    t.subjects.append(s)

        # Activate this version.
        for e in db.scalars(select(TimetableEntry)).all():
            e.is_active = False
        db.add_all(entries)
        db.flush()
        for e in entries:
            e.is_active = True
        db.commit()

        print(f"Imported timetable v{version}: {len(entries)} period-slots "
              f"across {len(all_classes)} classes.")
        print("  Per teacher (period-slots incl. both halves of a lab block):")
        for key in TEACHERS:
            print(f"    {TEACHERS[key][1]:<26} {counts.get(key, 0)}")
        if conflicts:
            print(f"\n  {len(conflicts)} clash/issue(s):")
            for c in conflicts:
                print(f"    - {c}")
        else:
            print("\n  No clashes. Every period placed exactly as transcribed.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
