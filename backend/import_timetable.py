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

SCHEDULE: dict[str, list[tuple]] = {
    # ---- Mr. Sameeran: S5 BCA GEN AI, S3 BCA AI CN, S3 BCA GE ----
    "sameeran@college.edu": [
        (MON, 3, "S5 BCA AI", "BCA-GENAI", None),
        (MON, 5, "S3 BCA AI", "BCA-CN", None),
        (TUE, 0, "S5 BCA AI", "BCA-GENAI", None),
        (WED, 1, "S5 BCA AI", "BCA-GENAI", None),
        (MON, 6, "S3 BCA AI", "BCA-CN", None),
        (THU, 2, "S3 BCA AI", "BCA-CN", None),
        (THU, 3, "S3 BCA AI", "BCA-CN", None),
        (FRI, 3, "S3 BCA AI", "BCA-CN", None),
    ],
    # ---- Dr. Sruthi: Digital (labs+theory), DSM, OS ----
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
        (THU, 4, "S3 BCA CS", "BCA-OS", None),
        (FRI, 0, "S1 BCA AI-B", "BCA-DIGITAL", None),
        (FRI, 1, "S1 BCA CS-A", "BCA-DIGITAL", None),
        (FRI, 2, "S1 BCA CS-B", "BCA-DSM", None),
        (FRI, 5, "S3 BCA AI", "BCA-OS", None),
        (SAT, 2, "S1 BCA CS-A", "BCA-DIGITAL", None),
        (SAT, 3, "S1 BCA AI-B", "BCA-DIGITAL", None),
    ],
    # ---- Dr. Nisha: NLP, DBMS, DSA, DSM ----
    "nisha@college.edu": [
        (MON, 1, "S5 BCA AI", "BCA-NLP", None),
        (MON, 4, "S3 BCA DA", "BCA-DBMS", None),
        (TUE, 2, "S5 BCA AI", "BCA-NLP", None),
        (TUE, 4, "S3 BCA DA", "BCA-DBMS", None),
        (WED, 2, "S1 BCA AI-B", "BCA-DSM", None),
        (WED, 4, "S3 BCA DA", "BCA-DBMSLAB", "ADMIN"),
        (THU, 1, "S1 BCA AI-A", "BCA-DSM", None),
        (FRI, 1, "S5 BCA AI", "BCA-NLP", None),
        (FRI, 2, "S1 BCA AI-B", "BCA-DSM", None),
        (SAT, 0, "S1 BCA AI-A", "BCA-DSM", None),
        (SAT, 4, "S3 BCA DA", "BCA-DBMS", None),
    ],
    # ---- Mr. Sanjay: Digital, CLDA ----
    "sanjay@college.edu": [
        (MON, 1, "S1 BCA CS-B", "BCA-DIGITAL", None),
        (MON, 3, "S5 BCA DA+Gen", "BCA-CLDA", None),
        (TUE, 0, "S5 BCA DA+Gen", "BCA-CLDA", None),
        (TUE, 1, "S1 BCA CS-B", "BCA-DIGITAL", None),
        (WED, 3, "S5 BCA DA+Gen", "BCA-CLDA", None),
        (THU, 0, "S1 BCA CS-B", "BCA-DIGILAB", None),
        (FRI, 0, "S1 BCA CS-B", "BCA-DIGITAL", None),
        (SAT, 0, "S1 BCA CS-B", "BCA-DIGITAL", None),
        (SAT, 2, "S1 BCA CS-B", "BCA-DIGITAL", None),
    ],
    # ---- Mr. Vipin: Digital Forensics, Cyber Forensics (S5 BCA CS) ----
    "vipin@college.edu": [
        (MON, 2, "S5 BCA CS", "BCA-DF", None),
        (MON, 3, "S5 BCA CS", "BCA-DF", None),
        (MON, 4, "S5 BCA CS", "BCA-CF", None),
        (MON, 7, "S5 BCA CS", "BCA-FORENSICSLAB", "DIGI"),
        (TUE, 2, "S5 BCA CS", "BCA-DF", "DIGI"),
        (TUE, 5, "S5 BCA CS", "BCA-CF", None),
        (WED, 2, "S5 BCA CS", "BCA-DF", None),
        (SAT, 5, "S5 BCA CS", "BCA-CF", None),
    ],
    # ---- Dr. Manivasagam: PFUC is non-BCA-core; keep only BCA labs? Grid is MCA-heavy.
    # BCA-relevant: none clearly BCA (S3 MCA NLP, S1 MCA Python, PFUC). Skip -> empty.
    "manivasagam@college.edu": [],
    # ---- Dr. Rajeev: S5 BCA AI DL (+lab), Python labs are MCA. BCA: DL. ----
    "rajeev@college.edu": [
        (MON, 0, "S5 BCA AI", "BCA-DL", None),
        (MON, 2, "S5 BCA AI", "BCA-MLLAB", "ADMIN"),
        (TUE, 1, "S5 BCA AI", "BCA-DL", None),
        (WED, 1, "S5 BCA AI", "BCA-DL", None),
        (THU, 0, "S5 BCA AI", "BCA-DL", None),
    ],
    # ---- Dr. Hari Narayanan: S3 BCA CS Python(+lab), DBMS, S3 BCA DA Python ----
    "hari@college.edu": [
        (MON, 4, "S3 BCA CS", "BCA-PYLAB", "ADMIN"),
        (TUE, 4, "S3 BCA CS", "BCA-DBMS", None),
        (TUE, 5, "S3 BCA DA", "BCA-PY", None),
        (THU, 4, "S3 BCA CS", "BCA-DBMS", None),
        (THU, 5, "S3 BCA DA", "BCA-PY", None),
        (FRI, 3, "S3 BCA CS", "BCA-DBMSLAB", "ADMIN"),
        (SAT, 4, "S3 BCA CS", "BCA-DBMS", None),
        (SAT, 6, "S3 BCA DA", "BCA-PY", None),
    ],
    # ---- Dr. Spurgen Ratheash: S5 BCA DWDM(+lab), S1 Python(+lab), S3 BCA CS CN ----
    "spurgen@college.edu": [
        (MON, 0, "S5 BCA DA+Gen", "BCA-DWDM", None),
        (MON, 3, "S1 BCA AI-B", "BCA-PY", None),
        (MON, 7, "S3 BCA CS", "BCA-CN", None),
        (TUE, 0, "S1 BCA AI-B", "BCA-PYLAB", "ADMIN"),
        (TUE, 7, "S3 BCA CS", "BCA-CN", None),
        (WED, 0, "S5 BCA DA+Gen", "BCA-DWDM", None),
        (WED, 2, "S5 BCA DA+Gen", "BCA-DWDM", None),
        (WED, 4, "S3 BCA CS", "BCA-CN", None),
        (WED, 6, "S1 BCA AI-B", "BCA-PYLAB", "DIGI"),
        (THU, 4, "S1 BCA AI-B", "BCA-PY", None),
        (FRI, 1, "S5 BCA DA+Gen", "BCA-DWDM", None),
        (FRI, 2, "S1 BCA AI-B", "BCA-PY", None),
        (FRI, 3, "S1 BCA AI-B", "BCA-DSA", None),
        (SAT, 1, "S1 BCA AI-B", "BCA-PY", None),
        (SAT, 2, "S1 BCA AI-B", "BCA-DSA", None),
    ],
    # ---- Dr. Meenu Suresh: S5 R Prog(+lab), S3 BCA CS Python, DBMS lab ----
    "meenu@college.edu": [
        (MON, 1, "S5 BCA DA+Gen", "BCA-RPROG", None),
        (MON, 2, "S5 BCA DA+Gen", "BCA-RPROG", None),
        (TUE, 2, "S5 BCA DA+Gen", "BCA-RPROG", "ADMIN"),
        (TUE, 4, "S3 BCA CS", "BCA-PY", None),
        (WED, 4, "S3 BCA CS", "BCA-PY", None),
        (THU, 0, "S5 BCA DA+Gen", "BCA-RPROG", None),
        (FRI, 4, "S3 BCA CS", "BCA-DBMSLAB", "ADMIN"),
        (SAT, 6, "S3 BCA CS", "BCA-PY", None),
    ],
    # ---- Mr. Joseph James: S5 BCA AI ML(+lab), S3 BCA AI Python, DL lab ----
    "joseph@college.edu": [
        (MON, 2, "S5 BCA AI", "BCA-MLLAB", "ADMIN"),
        (WED, 0, "S5 BCA AI", "BCA-ML", None),
        (WED, 2, "S5 BCA AI", "BCA-ML", None),
        (WED, 5, "S3 BCA AI", "BCA-PY", None),
        (THU, 0, "S5 BCA AI", "BCA-DL", None),
        (THU, 5, "S3 BCA AI", "BCA-PY", None),
        (FRI, 0, "S5 BCA AI", "BCA-ML", None),
        (SAT, 6, "S3 BCA AI", "BCA-PY", None),
    ],
    # ---- Ms. Soumya K: S1 BCA AI Digital(+lab), S5 BCA CS Crypto, S3 BCA AI DBMS, S3 BCA DA OS ----
    "soumya@college.edu": [
        (MON, 0, "S1 BCA AI-A", "BCA-DIGILAB", "ADMIN"),
        (MON, 6, "S3 BCA AI", "BCA-PYLAB", "ADMIN"),
        (TUE, 0, "S1 BCA AI-A", "BCA-DIGITAL", None),
        (TUE, 4, "S3 BCA AI", "BCA-DBMS", None),
        (TUE, 6, "S3 BCA AI", "BCA-DBMS", None),
        (WED, 0, "S5 BCA CS", "BCA-CRYPTO", None),
        (WED, 7, "S3 BCA DA", "BCA-OS", None),
        (THU, 0, "S1 BCA AI-A", "BCA-DIGITAL", None),
        (THU, 1, "S5 BCA CS", "BCA-CRYPTO", None),
        (THU, 5, "S3 BCA DA", "BCA-OS", None),
        (FRI, 1, "S5 BCA CS", "BCA-CRYPTO", None),
        (FRI, 4, "S3 BCA AI", "BCA-DBMS", None),
        (FRI, 5, "S3 BCA DA", "BCA-OS", None),
        (SAT, 0, "S1 BCA AI-A", "BCA-DIGITAL", None),
        (SAT, 4, "S3 BCA AI", "BCA-DBMS", None),
    ],
    # ---- Dr. Andal V: S5 BCA CS Pentest(+lab), S1 BCA CS Python(theory+lab) ----
    "andal@college.edu": [
        (MON, 0, "S5 BCA CS", "BCA-PENTEST", "DIGI"),
        (MON, 2, "S1 BCA CS-A", "BCA-PYLAB", "DIGI"),
        (TUE, 0, "S5 BCA CS", "BCA-PENTEST", None),
        (WED, 0, "S1 BCA CS-B", "BCA-PYLAB", "DIGI"),
        (THU, 0, "S5 BCA CS", "BCA-PENTEST", None),
        (THU, 1, "S1 BCA CS-A", "BCA-PY", None),
        (FRI, 2, "S1 BCA CS-A", "BCA-PY", None),
        (FRI, 3, "S1 BCA CS-B", "BCA-PY", None),
        (SAT, 0, "S5 BCA CS", "BCA-PENTEST", None),
        (SAT, 1, "S1 BCA CS-B", "BCA-PY", None),
        (SAT, 2, "S1 BCA CS-A", "BCA-PY", None),
        (SAT, 3, "S1 BCA CS-B", "BCA-PY", None),
    ],
    # ---- Mrs. Anjana Chandran (HOD): light BCA load (AI) ----
    "anjana@college.edu": [
        (TUE, 3, "S1 BCA AI-A", "BCA-AI", None),
        (THU, 3, "S1 BCA AI-A", "BCA-AI", None),
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
        lecture_rooms = [rooms["Room-1"], rooms["Room-2"], rooms["Room-3"]]

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

        for email, periods in SCHEDULE.items():
            teacher = teachers.get(email)
            if teacher is None:
                conflicts.append(f"Unknown teacher email: {email}")
                continue
            for day, pidx, class_name, subj_code, lab in periods:
                slot = slots.get((day, pidx))
                subject = subjects.get(subj_code)
                cls = classes.get(class_name)
                label = f"{class_name} {subj_code} ({teacher.name})"
                if slot is None:
                    conflicts.append(f"Bad slot d{day}p{pidx} for {label}")
                    continue
                if subject is None:
                    conflicts.append(f"Unknown subject {subj_code} for {label}")
                    continue
                if cls is None:
                    conflicts.append(f"Unknown class {class_name} for {label}")
                    continue

                # Faithful import: reproduce every period from each teacher's
                # grid as shown. We ONLY guard against the same teacher being in
                # two places at once (that can only be a mis-read of the photo).
                # Class overlaps between two teachers' grids are kept as-is, since
                # the individual photos are the source of truth.
                tkey = (slot.id, teacher.id)
                ckey = (slot.id, cls.id)
                if tkey in teacher_busy:
                    conflicts.append(
                        f"TEACHER CLASH (skipped): {teacher.name} double-booked d{day}p{pidx}: "
                        f"{teacher_busy[tkey]} vs {label}"
                    )
                    continue

                # Room selection.
                if lab == "ADMIN":
                    room = rooms["Admin Lab"]
                elif lab == "DIGI":
                    room = rooms["Digi Lab"]
                elif subject.is_lab:
                    room = rooms["Digi Lab"]
                else:
                    # pick first free lecture room this slot
                    room = None
                    for r in lecture_rooms:
                        if (slot.id, r.id) not in room_busy:
                            room = r
                            break
                    if room is None:
                        room = lecture_rooms[0]  # allow shared lecture hall if all busy

                # Record.
                teacher_busy[tkey] = label
                class_busy[ckey] = label
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
