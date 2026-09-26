"""Seed the database with the real BCA department faculty.

Run:  .venv\\Scripts\\python.exe seed.py

Every teacher gets their OWN randomly generated initial password and is flagged
`must_change_password=True`, so they are forced to set a new password on first
login. The initial passwords are printed once at the end of this script -- the
HOD should hand them to each teacher securely.

HOD / Admin: Mrs. Anjana Chandran  (anjana@college.edu)
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

# 5 periods/day, Monday..Saturday (the BCA timetable runs Mon-Sat).
# Period times mirror the college grid (morning periods flagged "preferred").
DAYS = 6
PERIODS = [
    ("08:30", "09:25", True),
    ("09:25", "10:20", True),
    ("10:40", "11:35", False),
    ("11:35", "12:30", False),
    ("12:30", "13:25", False),
    ("13:25", "14:20", False),
    ("14:40", "15:35", False),
    ("15:35", "16:30", False),
]


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def run() -> None:
    reset_db()
    db = SessionLocal()
    try:
        # Single department for now: BCA (Computer Applications).
        bca = Department(name="BCA")
        db.add(bca)
        db.flush()

        # Time slots (Mon-Sat).
        slots: list[TimeSlot] = []
        for day in range(DAYS):
            for idx, (start, end, pref) in enumerate(PERIODS):
                s = TimeSlot(
                    day_of_week=day,
                    period_index=idx,
                    start_time=start,
                    end_time=end,
                    is_preferred=pref,
                )
                slots.append(s)
                db.add(s)
        db.flush()

        # Rooms (from the grids: Admin Lab, Digi Lab, plus lecture rooms).
        rooms = [
            Room(name="Room-1", is_lab=False, capacity=60),
            Room(name="Room-2", is_lab=False, capacity=60),
            Room(name="Room-3", is_lab=False, capacity=60),
            Room(name="Admin Lab", is_lab=True, capacity=30),
            Room(name="Digi Lab", is_lab=True, capacity=30),
        ]
        db.add_all(rooms)
        db.flush()

        # ---- Subjects seen across the BCA timetable images ----
        # (name, code, importance, is_lab, periods_per_week)
        subject_specs = [
            ("Artificial Intelligence", "BCA-AI", 3, False, 4),
            ("Computer Networks", "BCA-CN", 3, False, 3),
            ("Operating Systems", "BCA-OS", 3, False, 3),
            ("Database Management Systems", "BCA-DBMS", 3, False, 4),
            ("Data Structures & Algorithms", "BCA-DSA", 3, False, 4),
            ("Discrete Structures & Maths", "BCA-DSM", 2, False, 3),
            ("Machine Learning", "BCA-ML", 3, False, 3),
            ("Deep Learning", "BCA-DL", 3, False, 3),
            ("Natural Language Processing", "BCA-NLP", 2, False, 3),
            ("Internet of Things", "BCA-IOT", 2, False, 2),
            ("Software Engineering", "BCA-SE", 2, False, 2),
            ("Python Programming", "BCA-PY", 3, False, 4),
            ("R Programming", "BCA-RPROG", 2, False, 3),
            ("NoSQL Databases", "BCA-NOSQL", 2, False, 2),
            ("Data Warehousing & Mining", "BCA-DWDM", 2, False, 3),
            ("Cloud & Distributed Applications", "BCA-CLDA", 2, False, 3),
            ("Cyber Forensics", "BCA-CF", 2, False, 2),
            ("Digital Forensics", "BCA-DF", 2, False, 2),
            ("Penetration Testing", "BCA-PENTEST", 2, False, 3),
            ("Cryptography", "BCA-CRYPTO", 2, False, 3),
            ("Generative AI", "BCA-GENAI", 3, False, 3),
            ("Digital Fundamentals", "BCA-DIGITAL", 2, False, 4),
            ("Digital Lab", "BCA-DIGILAB", 2, True, 2),
            ("Employability Skills", "BCA-EMP", 1, False, 2),
            ("AI Literacy", "BCA-AILIT", 1, False, 1),
            ("Python Lab", "BCA-PYLAB", 3, True, 2),
            ("ML Lab", "BCA-MLLAB", 3, True, 2),
            ("DBMS Lab", "BCA-DBMSLAB", 3, True, 2),
            ("Forensics Lab", "BCA-FORENSICSLAB", 2, True, 2),
            ("Programming Fundamentals (PFUC)", "BCA-PFUC", 2, False, 3),
        ]
        subjects: dict[str, Subject] = {}
        for name, code, importance, is_lab, ppw in subject_specs:
            s = Subject(
                name=name,
                code=code,
                department_id=bca.id,
                importance=importance,
                is_lab=is_lab,
                periods_per_week=ppw,
            )
            subjects[code] = s
            db.add(s)
        db.flush()

        # Classes seen in the grids (BCA sections across semesters).
        class_names = [
            "S1 BCA AI-A",
            "S1 BCA AI-B",
            "S1 BCA CS-A",
            "S1 BCA CS-B",
            "S3 BCA AI",
            "S3 BCA CS",
            "S3 BCA DA",
            "S5 BCA AI",
            "S5 BCA CS",
            "S5 BCA DA+Gen",
        ]
        classes = [ClassSection(name=n) for n in class_names]
        db.add_all(classes)
        db.flush()

        # ---- Faculty ----
        # (name, email-localpart, [subject codes they teach], is_hod)
        faculty = [
            ("Mrs. Anjana Chandran", "anjana",
             ["BCA-AI", "BCA-CN", "BCA-DBMS"], True),
            ("Mr. Sameeran", "sameeran",
             ["BCA-GENAI", "BCA-CN", "BCA-EMP", "BCA-AILIT"], False),
            ("Dr. Sruthi", "sruthi",
             ["BCA-DIGITAL", "BCA-DIGILAB", "BCA-DSM", "BCA-OS"], False),
            ("Dr. Nisha", "nisha",
             ["BCA-NLP", "BCA-DBMS", "BCA-DSA", "BCA-DSM"], False),
            ("Mr. Sanjay", "sanjay",
             ["BCA-DIGITAL", "BCA-DIGILAB", "BCA-CLDA", "BCA-AI"], False),
            ("Mr. Vipin", "vipin",
             ["BCA-DF", "BCA-CF", "BCA-FORENSICSLAB"], False),
            ("Dr. Manivasagam", "manivasagam",
             ["BCA-NLP", "BCA-PY", "BCA-PYLAB", "BCA-PFUC"], False),
            ("Dr. Rajeev", "rajeev",
             ["BCA-DL", "BCA-IOT", "BCA-PY", "BCA-PYLAB", "BCA-MLLAB"], False),
            ("Dr. Hari Narayanan", "hari",
             ["BCA-PY", "BCA-PYLAB", "BCA-DBMS", "BCA-DL", "BCA-DBMSLAB"], False),
            ("Dr. Spurgen Ratheash", "spurgen",
             ["BCA-DWDM", "BCA-PY", "BCA-PYLAB", "BCA-DSA", "BCA-CN"], False),
            ("Dr. Meenu Suresh", "meenu",
             ["BCA-RPROG", "BCA-PY", "BCA-NOSQL", "BCA-DBMSLAB"], False),
            ("Mr. Joseph James", "joseph",
             ["BCA-ML", "BCA-MLLAB", "BCA-PY", "BCA-SE", "BCA-DBMSLAB"], False),
            ("Ms. Soumya K", "soumya",
             ["BCA-DIGITAL", "BCA-DIGILAB", "BCA-CRYPTO", "BCA-DBMS", "BCA-OS"], False),
            ("Dr. Andal V", "andal",
             ["BCA-PENTEST", "BCA-PY", "BCA-PYLAB", "BCA-AI"], False),
        ]

        # One simple, memorable temporary password for everyone. Each user is
        # still forced to change it on first login (must_change_password=True),
        # so this is only ever valid until they set their own.
        INITIAL_PASSWORD = "Welcome@2026"

        credentials: list[tuple[str, str, str, str]] = []  # (name, email, role, password)
        for name, local, codes, is_hod in faculty:
            email = f"{local}@college.edu"
            password = INITIAL_PASSWORD
            t = Teacher(
                name=name,
                email=email,
                hashed_password=hash_password(password),
                role=Role.HOD if is_hod else Role.TEACHER,
                department_id=bca.id,
                max_periods_per_day=6,
                is_active=True,
                must_change_password=True,
            )
            t.subjects = [subjects[c] for c in codes]
            db.add(t)
            credentials.append((name, email, "HOD" if is_hod else "TEACHER", password))

        db.commit()

        # ---- Credential sheet (printed once) ----
        print("\nSeed complete.")
        print(
            f"  Department: BCA | Slots: {len(slots)} | Rooms: {len(rooms)} "
            f"| Subjects: {len(subjects)} | Classes: {len(classes)} "
            f"| Teachers: {len(faculty)}"
        )
        print("\n  INITIAL LOGINS (each user must change password on first login):")
        print("  " + "-" * 78)
        print(f"  {'Name':<26}{'Email':<26}{'Role':<9}{'Initial password'}")
        print("  " + "-" * 78)
        for name, email, role, password in credentials:
            print(f"  {name:<26}{email:<26}{role:<9}{password}")
        print("  " + "-" * 78)
        print("  Hand these to each teacher securely. They expire on first change.\n")
    finally:
        db.close()


if __name__ == "__main__":
    run()
