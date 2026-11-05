"""Idempotent production seed — runs only when the DB is empty.

Safe to call on a live server at any time.  If teachers already exist it does
nothing, so it never wipes real leave / substitution data.

What it does on a fresh DB:
  1. Creates all tables (Base.metadata.create_all).
  2. Runs seed.py to create teachers, classes, subjects, rooms and time-slots.
  3. Runs import_images_timetable.py to load the department's real 218-period
     timetable (the one transcribed from the 14 teacher grids).

Render / Fly: add this as the start command or call it in a release command:
    python seed_once.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""
from sqlalchemy import select

from app.database import SessionLocal, Base, engine
from app.models import Teacher, TimetableEntry


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.scalar(select(Teacher).limit(1))
        if existing:
            print("Database already has data — skipping seed.")
            # Still run the importer if there are no timetable entries.
            active = db.scalar(select(TimetableEntry).where(TimetableEntry.is_active.is_(True)).limit(1))
            if not active:
                print("No active timetable found — running importer.")
                db.close()
                import import_images_timetable
                import_images_timetable.run()
            return
    finally:
        try:
            db.close()
        except Exception:
            pass

    # Empty DB: seed reference data first, then import real timetable.
    print("Empty database — seeding...")
    import seed
    seed.run()
    print("Importing real timetable from teacher grids...")
    import import_images_timetable
    import_images_timetable.run()
    print("Done.")


if __name__ == "__main__":
    main()

