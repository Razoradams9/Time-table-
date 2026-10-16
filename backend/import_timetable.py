"""Import the real BCA timetable from the department's teacher grids.

Run:  .venv\\Scripts\\python.exe import_timetable.py

Encodes every BCA period from the 13 teacher timetables as TimetableEntry rows,
inserts them as a new version, and marks that version active so it shows up in
"My Timetable" for the HOD and each teacher.

Scope decisions (per the department, BCA-only):
  * Non-BCA periods (MCA, B.Sc.IT, PFUC, generic Emp-Skill/AI-Literacy) are skipped.
  * Lab periods naming two teachers are assigned to the first-named teacher.
  * Lab periods use the room named in the grid (Admin Lab / Digi Lab); lectures
    are placed in lecture rooms (Room-1..3), chosen to avoid clashes.

Days:    0=Mon 1=Tue 2=Wed 3=Thu 4=Fri 5=Sat
Periods: 0=08:30 1=09:25 2=10:40 3=11:35 4=12:30 5=13:25 6=14:40 7=15:35
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    ClassSection,
    Room,
    Subject,
    Teacher,
    TimeSlot,
    TimetableEntry,
)

# Day / period aliases so the schedule below reads like the grid.
MON, TUE, WED, THU, FRI, SAT = range(6)

# A period entry: (day, period_index, class_name, subject_code, is_lab_room)
# is_lab_room: "ADMIN", "DIGI", or None (lecture room auto-assigned).
#
# Each teacher's list encodes only their BCA periods from the photo.
# subject codes come from seed.py: BCA-AI, BCA-CN, BCA-OS, BCA-DBMS, BCA-DSA,
# BCA-DSM, BCA-ML, BCA-DL, BCA-NLP, BCA-PY, BCA-RPROG, BCA-NOSQL, BCA-DWDM,
# BCA-CLDA, BCA-CF, BCA-DF, BCA-PENTEST, BCA-CRYPTO, BCA-GENAI, BCA-DIGITAL,
# and the *LAB codes.

# Faithful transcription of all 13 teacher photos. Each tuple:
#   (day, period_index, class_name, subject_code, lab_room_hint)
# Co-taught labs are assigned to the first-named teacher. B.SC.CSIT and PFUC
# are NOT imported as classes but ARE reserved as teacher-busy blockers (see
# BLOCKERS below) so no BCA/MCA period overlaps them.
SCHEDULE: dict[str, list[tuple]] = {
    # ---- Mr. SAMEERAN ----
    "sameeran@college.edu": [
        (MON, 3, "S5 BCA AI", "BCA-GENAI", None),
        (MON, 5, "S3 BCA AI", "BCA-CN", None),
        (TUE, 0, "S5 BCA AI", "BCA-GENAI", None),
        (TUE, 3, "S1 MCA A", "MCA-EMP", None),
        (WED, 1, "S5 BCA AI", "BCA-GENAI", None),
        (WED, 3, "S1 MCA B", "MCA-EMP", None),
        (WED, 5, "S3 BCA AI", "BCA-CN", None),
        (THU, 2, "S5 BCA AI", "BCA-GE", None),
        (THU, 3, "S5 BCA AI", "BCA-GE", None),
        (THU, 6, "S3 BCA AI", "BCA-GE", None),
        (THU, 7, "S3 BCA AI", "BCA-GE", None),
        (FRI, 3, "S5 BCA AI", "BCA-GE", None),
        (FRI, 5, "S1 MCA A", "MCA-EMP", None),
    ],
    # ---- Dr. SRUTHI ----
    "sruthi@college.edu": [
        (MON, 0, "S1 BCA AI-B", "BCA-DIGILAB", "ADMIN"),
        (MON, 2, "S3 BCA CS", "BCA-DSM", None),
        (MON, 5, "S3 BCA AI", "BCA-OS", None),
        (MON, 6, "S3 BCA CS", "BCA-OS", None),
        (TUE, 0, "S1 BCA CS-A", "BCA-DIGILAB", "DIGI"),
        (WED, 3, "S1 BCA AI-B", "BCA-DIGITAL", None),
        (WED, 6, "S3 BCA CS", "BCA-OS", None),
        (WED, 7, "S3 BCA AI", "BCA-OS", None),
        (THU, 0, "S1 BCA CS-A", "BCA-DIGITAL", None),
        (THU, 5, "S3 BCA CS", "BCA-OS", None),
        (FRI, 0, "S1 BCA AI-B", "BCA-DIGITAL", None),
        (FRI, 2, "S1 BCA CS-B", "BCA-DSM", None),
        (FRI, 5, "S3 BCA AI", "BCA-OS", None),
        (SAT, 3, "S1 BCA CS-A", "BCA-DIGITAL", None),
        (SAT, 4, "S1 BCA AI-B", "BCA-DIGITAL", None),
    ],
    # ---- Dr. NISHA ----
    "nisha@college.edu": [
        (MON, 1, "S5 BCA AI", "BCA-NLP", None),
        (MON, 4, "S3 BCA DA", "BCA-DBMS", None),
        (MON, 5, "S1 MCA B", "MCA-DSA", None),
        (TUE, 2, "S5 BCA AI", "BCA-NLP", None),
        (TUE, 4, "S3 BCA DA", "BCA-DBMS", None),
        (WED, 2, "S1 BCA AI-B", "BCA-DSM", None),
        (WED, 4, "S3 BCA DA", "BCA-DBMSLAB", "ADMIN"),
        (WED, 5, "S3 BCA DA", "BCA-DBMSLAB", "ADMIN"),
        (THU, 1, "S1 BCA AI-A", "BCA-DSM", None),
        (FRI, 1, "S5 BCA AI", "BCA-NLP", None),
        (FRI, 3, "S1 BCA AI-B", "BCA-DSM", None),
        (FRI, 4, "S1 MCA B", "MCA-DSA", None),
        (FRI, 5, "S1 MCA B", "MCA-DSALAB", "ADMIN"),
        (SAT, 3, "S1 MCA B", "MCA-DSALAB", "ADMIN"),
        (SAT, 5, "S3 BCA DA", "BCA-DBMS", None),
        (SAT, 7, "S1 MCA B", "MCA-DSA", None),
    ],
    # ---- Mr. SANJAY (B.SC.CSIT skipped as class; reserved as blocker) ----
    "sanjay@college.edu": [
        (MON, 1, "S1 BCA CS-B", "BCA-DIGITAL", None),
        (MON, 4, "S5 BCA DA+Gen", "BCA-CLDA", None),
        (MON, 5, "S1 MCA B", "MCA-AI", None),
        (TUE, 0, "S5 BCA DA+Gen", "BCA-CLDA", None),
        (TUE, 1, "S1 BCA CS-B", "BCA-DIGITAL", None),
        (TUE, 5, "S1 MCA B", "MCA-AI", None),
        (WED, 2, "S5 BCA DA+Gen", "BCA-CLDA", None),
        (THU, 0, "S1 BCA CS-B", "BCA-DIGILAB", None),
        (THU, 3, "S1 MCA B", "MCA-AI", None),
        (SAT, 0, "S1 BCA CS-B", "BCA-DIGITAL", None),
    ],
    # ---- Mr. VIPIN (all S5 BCA CS forensics) ----
    "vipin@college.edu": [
        (MON, 2, "S5 BCA CS", "BCA-DF", None),
        (MON, 3, "S5 BCA CS", "BCA-DF", None),
        (MON, 4, "S5 BCA CS", "BCA-CF", None),
        (MON, 7, "S5 BCA CS", "BCA-FORENSICSLAB", "DIGI"),
        (TUE, 2, "S5 BCA CS", "BCA-FORENSICSLAB", "DIGI"),
        (TUE, 3, "S5 BCA CS", "BCA-DF", None),
        (TUE, 5, "S5 BCA CS", "BCA-CF", None),
        (WED, 2, "S5 BCA CS", "BCA-DF", None),
        (SAT, 5, "S5 BCA CS", "BCA-CF", None),
    ],
    # ---- Dr. MANIVASAGAM (PFUC skipped as class; reserved as blocker) ----
    "manivasagam@college.edu": [
        (MON, 4, "S3 MCA GEN", "MCA-NLPLAB", "DIGI"),
        (MON, 5, "S1 MCA B", "MCA-PYLAB", "DIGI"),
        (MON, 7, "S3 MCA GEN", "MCA-PY", None),
        (TUE, 5, "S3 MCA GEN", "MCA-NLP", None),
        (TUE, 6, "S3 MCA GEN", "MCA-NLP", None),
        (WED, 5, "S3 MCA GEN", "MCA-PY", None),
        (THU, 4, "S3 MCA GEN", "MCA-NLPLAB", "DIGI"),
        (FRI, 4, "S3 MCA GEN", "MCA-NLP", None),
        (SAT, 4, "S3 MCA GEN", "MCA-NLPLAB", "DIGI"),
        (SAT, 5, "S3 MCA GEN", "MCA-PY", None),
    ],
    # ---- Dr. RAJEEV ----
    "rajeev@college.edu": [
        (MON, 0, "S5 BCA AI", "BCA-DL", None),
        (MON, 2, "S5 BCA AI", "BCA-MLLAB", "ADMIN"),
        (MON, 5, "S3 MCA GEN", "MCA-IOT", None),
        (TUE, 1, "S5 BCA AI", "BCA-DL", None),
        (TUE, 6, "S1 MCA A", "MCA-PY", None),
        (TUE, 7, "S3 MCA GEN", "MCA-IOT", None),
        (WED, 1, "S5 BCA AI", "BCA-DL", None),
        (WED, 3, "S1 MCA A", "MCA-PY", None),
        (WED, 4, "S1 MCA A", "MCA-PYLAB", "DIGI"),
        (WED, 5, "S1 MCA A", "MCA-PYLAB", "DIGI"),
        (THU, 0, "S5 BCA AI", "BCA-MLLAB", "ADMIN"),
        (SAT, 3, "S3 MCA GEN", "MCA-IOT", None),
        (SAT, 7, "S1 MCA A", "MCA-PY", None),
    ],
    # ---- Dr. HARI NARAYANAN ----
    "hari@college.edu": [
        (MON, 4, "S3 BCA CS", "BCA-PYLAB", "ADMIN"),
        (MON, 7, "S3 MCA CS", "MCA-AI", None),
        (TUE, 4, "S3 BCA CS", "BCA-DBMS", None),
        (TUE, 5, "S3 BCA DA", "BCA-PY", None),
        (TUE, 6, "S3 BCA DA", "BCA-PYLAB", "ADMIN"),
        (WED, 5, "S3 MCA CS", "MCA-AI", None),
        (WED, 6, "S3 MCA CS", "MCA-AI", None),
        (THU, 4, "S3 BCA CS", "BCA-DBMS", None),
        (THU, 5, "S3 BCA DA", "BCA-PY", None),
        (FRI, 4, "S3 MCA CS", "MCA-AI", None),
        (FRI, 5, "S3 BCA CS", "BCA-DBMSLAB", "ADMIN"),
        (SAT, 4, "S3 BCA CS", "BCA-DBMS", None),
        (SAT, 6, "S3 BCA DA", "BCA-PY", None),
    ],
    # ---- Dr. SPURGEN RATHEASH ----
    "spurgen@college.edu": [
        (MON, 0, "S5 BCA DA+Gen", "BCA-DWDM", None),
        (MON, 3, "S1 BCA AI-B", "BCA-PY", None),
        (MON, 4, "S1 MCA A", "MCA-DSA", None),
        (MON, 7, "S3 BCA CS", "BCA-CN", None),
        (TUE, 0, "S1 BCA AI-B", "BCA-PYLAB", "ADMIN"),
        (TUE, 7, "S3 BCA CS", "BCA-CN", None),
        (WED, 0, "S5 BCA DA+Gen", "BCA-DWDM", None),
        (WED, 2, "S5 BCA DA+Gen", "BCA-DWDMLAB", "DIGI"),
        (WED, 5, "S3 BCA CS", "BCA-CN", None),
        (WED, 6, "S1 MCA A", "MCA-DSALAB", "DIGI"),
        (THU, 5, "S1 MCA A", "MCA-DSA", None),
        (FRI, 1, "S5 BCA DA+Gen", "BCA-DWDM", None),
        (FRI, 3, "S1 BCA AI-B", "BCA-PY", None),
        (FRI, 4, "S1 MCA A", "MCA-DSALAB", None),
        (SAT, 0, "S1 BCA AI-B", "BCA-PY", None),
        (SAT, 3, "S1 MCA A", "MCA-DSA", None),
    ],
    # ---- Dr. MEENU SURESH ----
    "meenu@college.edu": [
        (MON, 1, "S5 BCA DA+Gen", "BCA-RPROG", None),
        (MON, 3, "S5 BCA DA+Gen", "BCA-RPROGLAB", "ADMIN"),
        (MON, 4, "S3 BCA CS", "BCA-PYLAB", "ADMIN"),
        (MON, 7, "S3 MCA GEN", "MCA-NOSQL", None),
        (TUE, 4, "S3 BCA CS", "BCA-PY", None),
        (WED, 4, "S3 BCA CS", "BCA-PY", None),
        (WED, 5, "S3 MCA GEN", "MCA-NOSQL", None),
        (THU, 0, "S5 BCA DA+Gen", "BCA-RPROG", None),
        (THU, 5, "S3 MCA GEN", "MCA-NOSQLLAB", "DIGI"),
        (FRI, 5, "S3 BCA CS", "BCA-DBMSLAB", "ADMIN"),
        (SAT, 3, "S3 MCA GEN", "MCA-NOSQL", None),
        (SAT, 6, "S3 BCA CS", "BCA-PY", None),
    ],
    # ---- Mr. JOSEPH JAMES ----
    "joseph@college.edu": [
        (MON, 2, "S5 BCA AI", "BCA-MLLAB", "ADMIN"),
        (MON, 5, "S3 MCA CS", "MCA-ML", None),
        (MON, 7, "S3 BCA AI", "BCA-PYLAB", "ADMIN"),
        (TUE, 5, "S3 BCA AI", "BCA-DBMSLAB", "ADMIN"),
        (TUE, 7, "S3 MCA CS", "MCA-ML", None),
        (WED, 0, "S5 BCA AI", "BCA-ML", None),
        (WED, 2, "S5 BCA AI", "BCA-ML", None),
        (WED, 4, "S3 MCA GEN", "MCA-SE", None),
        (WED, 5, "S3 BCA AI", "BCA-PY", None),
        (THU, 0, "S5 BCA AI", "BCA-DL", None),
        (THU, 5, "S3 BCA AI", "BCA-PY", None),
        (FRI, 0, "S5 BCA AI", "BCA-ML", None),
        (FRI, 4, "S3 MCA CS", "MCA-ML", None),
        (FRI, 5, "S3 MCA GEN", "MCA-SE", None),
        (SAT, 4, "S3 MCA CS", "MCA-ML", None),
        (SAT, 5, "S3 MCA GEN", "MCA-SE", None),
        (SAT, 6, "S3 BCA AI", "BCA-PY", None),
    ],
    # ---- Ms. SOUMYA K ----
    "soumya@college.edu": [
        (MON, 0, "S1 BCA AI-A", "BCA-DIGILAB", "ADMIN"),
        (MON, 6, "S3 BCA AI", "BCA-PY", None),
        (TUE, 0, "S1 BCA AI-A", "BCA-DIGITAL", None),
        (TUE, 5, "S3 BCA AI", "BCA-DBMSLAB", "ADMIN"),
        (TUE, 6, "S3 BCA AI", "BCA-DBMS", None),
        (WED, 0, "S5 BCA CS", "BCA-CRYPTO", None),
        (WED, 6, "S3 BCA DA", "BCA-OS", None),
        (THU, 0, "S1 BCA AI-A", "BCA-DIGITAL", None),
        (THU, 1, "S5 BCA CS", "BCA-CRYPTO", None),
        (THU, 5, "S3 BCA DA", "BCA-OS", None),
        (FRI, 1, "S5 BCA CS", "BCA-CRYPTO", None),
        (FRI, 5, "S3 BCA AI", "BCA-DBMS", None),
        (FRI, 6, "S3 BCA DA", "BCA-OS", None),
        (SAT, 0, "S1 BCA AI-A", "BCA-DIGITAL", None),
        (SAT, 5, "S3 BCA AI", "BCA-DBMS", None),
    ],
    # ---- Dr. ANDAL V ----
    "andal@college.edu": [
        (MON, 1, "S5 BCA CS", "BCA-PENTEST", "DIGI"),
        (MON, 3, "S1 BCA CS-A", "BCA-PYLAB", "DIGI"),
        (MON, 7, "S1 MCA A", "MCA-AI", None),
        (TUE, 1, "S5 BCA CS", "BCA-PENTEST", None),
        (WED, 0, "S1 BCA CS-B", "BCA-PYLAB", "DIGI"),
        (THU, 1, "S5 BCA CS", "BCA-PENTEST", None),
        (THU, 2, "S1 BCA CS-A", "BCA-PY", None),
        (THU, 5, "S1 MCA A", "MCA-AI", None),
        (FRI, 3, "S1 BCA CS-A", "BCA-PY", None),
        (FRI, 4, "S1 BCA CS-B", "BCA-PY", None),
        (SAT, 1, "S5 BCA CS", "BCA-PENTEST", None),
        (SAT, 2, "S1 BCA CS-B", "BCA-PY", None),
        (SAT, 3, "S1 BCA CS-A", "BCA-PY", None),
        (SAT, 4, "S1 MCA A", "MCA-AI", None),
    ],
    # ---- Mrs. ANJANA CHANDRAN (HOD) ----
    "anjana@college.edu": [
        (MON, 4, "S1 MCA A", "MCA-ACN", None),
        (MON, 6, "S1 MCA B", "MCA-ACN", None),
        (MON, 7, "S1 MCA A", "MCA-ACN", None),
        (TUE, 4, "S1 MCA B", "MCA-ACN", None),
        (WED, 5, "S3 MCA CS", "MCA-BC", None),
        (WED, 6, "S3 MCA CS", "MCA-BCLAB", "DIGI"),
        (WED, 7, "S3 MCA CS", "MCA-BCLAB", "DIGI"),
        (THU, 5, "S3 MCA CS", "MCA-BC", None),
        (FRI, 4, "S1 MCA A", "MCA-ACN", None),
        (SAT, 6, "S3 MCA CS", "MCA-BC", None),
    ],
}

# Non-BCA/MCA commitments that must NOT be overwritten. These do not create
# visible timetable entries, but they reserve the teacher's time so no BCA/MCA
# period is placed on top of them. (B.SC.CSIT for Sanjay, PFUC for Manivasagam.)
BLOCKERS: dict[str, list[tuple]] = {
    # (day, period_index) -- Sanjay's B.SC.CSIT Digital periods.
    "sanjay@college.edu": [
        (MON, 0),            # S1 B.SC.CSIT Digital
        (THU, 3),            # B.SC.CSIT Digital Lab (Admin)
        (FRI, 0),            # B.SC.CSIT Digital
        (SAT, 2),            # S1 B.SC.CSIT Digital
    ],
    # Manivasagam's PFUC + C Lab commitments.
    "manivasagam@college.edu": [
        (TUE, 1),            # PFUC Mani
        (THU, 1),            # PFUC Mani
        (FRI, 3),            # C Lab Manivasagam (Admin)
        (SAT, 1),            # PFUC Mani
    ],
}


def run() -> None:
    db = SessionLocal()
    try:
        # Clean slate: remove any previously imported/generated timetable entries
        # so we don't accumulate stale versions.
        deleted = db.query(TimetableEntry).delete()
        db.commit()
        if deleted:
            print(f"Cleared {deleted} existing timetable entries.")

        # Resolve reference maps.
        teachers = {t.email: t for t in db.scalars(select(Teacher)).all()}
        subjects = {s.code: s for s in db.scalars(select(Subject)).all()}
        classes = {c.name: c for c in db.scalars(select(ClassSection)).all()}
        rooms = {r.name: r for r in db.scalars(select(Room)).all()}
        slots = {
            (s.day_of_week, s.period_index): s
            for s in db.scalars(select(TimeSlot)).all()
        }
        lecture_rooms = [
            rooms[f"Room-{i}"] for i in range(1, 9) if f"Room-{i}" in rooms
        ]
        lab_room_list = [r for r in rooms.values() if r.is_lab]

        # Semester time windows: S1 & S5 BCA -> morning periods 0-3;
        # S3 BCA and ALL MCA -> evening periods 4-7.
        def window_for(class_name: str) -> list[int]:
            import re

            morning = [0, 1, 2, 3]
            evening = [4, 5, 6, 7]
            is_mca = "MCA" in class_name
            m = re.search(r"S(\d+)", class_name)
            sem = int(m.group(1)) if m else None
            if is_mca:
                return evening
            if sem in (1, 5):
                return morning
            if sem == 3:
                return evening
            return morning + evening

        # Next version number.
        existing = db.scalars(select(TimetableEntry.version)).all()
        version = (max(existing) + 1) if existing else 1

        # Occupancy trackers to detect and route around clashes.
        teacher_busy: dict[tuple, str] = {}   # (slot_id, teacher_id) -> label
        class_busy: dict[tuple, str] = {}      # (slot_id, class_id)  -> label
        room_busy: set[tuple] = set()          # (slot_id, room_id)
        conflicts: list[str] = []
        entries: list[TimetableEntry] = []
        counts: dict[str, int] = defaultdict(int)

        # Reserve non-BCA/MCA commitments (B.SC.CSIT, PFUC) as teacher-busy so
        # nothing is scheduled over them. No visible entry is created.
        for email, blocked in BLOCKERS.items():
            teacher = teachers.get(email)
            if teacher is None:
                continue
            for day, pidx in blocked:
                slot = slots.get((day, pidx))
                if slot is not None:
                    teacher_busy[(slot.id, teacher.id)] = "RESERVED (non-BCA/MCA)"

        def pick_room(slot_id: int, lab_hint, is_lab: bool):
            """Choose a free room for a slot: labs -> lab rooms, else lecture."""
            if lab_hint == "ADMIN" and (slot_id, rooms["Admin Lab"].id) not in room_busy:
                return rooms["Admin Lab"]
            if lab_hint == "DIGI" and (slot_id, rooms["Digi Lab"].id) not in room_busy:
                return rooms["Digi Lab"]
            pool = lab_room_list if is_lab else lecture_rooms
            for r in pool:
                if (slot_id, r.id) not in room_busy:
                    return r
            return pool[0] if pool else lecture_rooms[0]

        def find_slot(day: int, window: list[int], teacher_id: int, class_id: int):
            """Find a free (day, period) in the window: try the given day first,
            then any day. Free = teacher and class both open that slot."""
            day_order = [day] + [d for d in range(6) if d != day]
            for d in day_order:
                for p in window:
                    s = slots.get((d, p))
                    if not s:
                        continue
                    if (s.id, teacher_id) in teacher_busy:
                        continue
                    if (s.id, class_id) in class_busy:
                        continue
                    return s
            return None

        for email, periods in SCHEDULE.items():
            teacher = teachers.get(email)
            if teacher is None:
                conflicts.append(f"Unknown teacher email: {email}")
                continue
            for day, pidx, class_name, subj_code, lab in periods:
                subject = subjects.get(subj_code)
                cls = classes.get(class_name)
                label = f"{class_name} {subj_code} ({teacher.name})"
                if subject is None:
                    conflicts.append(f"Unknown subject {subj_code} for {label}")
                    continue
                if cls is None:
                    conflicts.append(f"Unknown class {class_name} for {label}")
                    continue

                window = window_for(class_name)
                # Prefer the exact photo slot IF it is in the class's window and
                # free; otherwise relocate into the correct window.
                slot = slots.get((day, pidx))
                in_window = slot is not None and pidx in window
                free = (
                    slot is not None
                    and (slot.id, teacher.id) not in teacher_busy
                    and (slot.id, cls.id) not in class_busy
                )
                if not (in_window and free):
                    slot = find_slot(day, window, teacher.id, cls.id)
                if slot is None:
                    conflicts.append(
                        f"No free slot in window for {label} (window={window})"
                    )
                    continue

                room = pick_room(slot.id, lab, subject.is_lab)

                teacher_busy[(slot.id, teacher.id)] = label
                class_busy[(slot.id, cls.id)] = label
                room_busy.add((slot.id, room.id))
                entries.append(
                    TimetableEntry(
                        version=version,
                        is_active=False,
                        time_slot_id=slot.id,
                        teacher_id=teacher.id,
                        subject_id=subject.id,
                        class_section_id=cls.id,
                        room_id=room.id,
                    )
                )
                counts[email] += 1

        # Activate this version, deactivate others.
        for e in db.scalars(select(TimetableEntry)).all():
            e.is_active = False
        db.add_all(entries)
        db.flush()
        for e in entries:
            e.is_active = True
        db.commit()

        print(f"\nImported timetable v{version}: {len(entries)} periods.")
        print("  Per teacher:")
        for email in SCHEDULE:
            print(f"    {email:<28} {counts.get(email, 0)} periods")
        if conflicts:
            print(f"\n  {len(conflicts)} issue(s) encountered (skipped):")
            for c in conflicts:
                print(f"    - {c}")
        else:
            print("\n  No conflicts. All periods imported cleanly.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
