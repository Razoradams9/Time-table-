"""Idempotent seed for production — only seeds if the DB is empty.

Safe to run on a live server: if teachers already exist it does nothing, so it
never wipes real leave/substitution data. Run once after the first deploy:

    fly ssh console -C "python seed_once.py"

To force a full reset locally, use seed.py instead.
"""
from sqlalchemy import select

from app.database import SessionLocal, Base, engine
from app.models import Teacher


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.scalar(select(Teacher).limit(1))
        if existing:
            print("Database already seeded — skipping.")
            return
    finally:
        db.close()
    # Empty DB: run the full seed.
    import seed
    seed.run()


if __name__ == "__main__":
    main()
