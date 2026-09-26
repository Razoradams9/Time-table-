"""SQLAlchemy ORM models for the timetable & substitution system."""
from __future__ import annotations

import enum
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    Column,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, enum.Enum):
    TEACHER = "TEACHER"
    HOD = "HOD"


class LeaveScope(str, enum.Enum):
    FULL_DAY = "FULL_DAY"
    PERIODS = "PERIODS"


class LeaveStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"


class SubstitutionStatus(str, enum.Enum):
    ASSIGNED = "ASSIGNED"
    UNCOVERED = "UNCOVERED"
    CANCELLED = "CANCELLED"


class SubstitutionSource(str, enum.Enum):
    AUTO = "AUTO"          # rule engine
    MANUAL = "MANUAL"      # HOD override
    SUGGESTION = "SUGGESTION"  # accepted AI suggestion


# Many-to-many: which subjects a teacher is qualified to teach.
teacher_subjects = Table(
    "teacher_subjects",
    Base.metadata,
    Column("teacher_id", ForeignKey("teachers.id", ondelete="CASCADE"), primary_key=True),
    Column("subject_id", ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True),
)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)

    teachers: Mapped[list[Teacher]] = relationship(back_populates="department")
    subjects: Mapped[list[Subject]] = relationship(back_populates="department")


class Teacher(Base):
    __tablename__ = "teachers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.TEACHER)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    max_periods_per_day: Mapped[int] = mapped_column(Integer, default=6)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    department: Mapped[Department | None] = relationship(back_populates="teachers")
    subjects: Mapped[list[Subject]] = relationship(secondary=teacher_subjects, back_populates="teachers")
    availability: Mapped[list[Availability]] = relationship(back_populates="teacher", cascade="all, delete-orphan")


class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(30), unique=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    importance: Mapped[int] = mapped_column(Integer, default=1)  # higher = more important
    is_lab: Mapped[bool] = mapped_column(Boolean, default=False)
    periods_per_week: Mapped[int] = mapped_column(Integer, default=4)

    department: Mapped[Department | None] = relationship(back_populates="subjects")
    teachers: Mapped[list[Teacher]] = relationship(secondary=teacher_subjects, back_populates="subjects")


class ClassSection(Base):
    __tablename__ = "class_sections"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)  # e.g. "CSE-3A"


class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    is_lab: Mapped[bool] = mapped_column(Boolean, default=False)
    capacity: Mapped[int] = mapped_column(Integer, default=60)


class TimeSlot(Base):
    """A period on a given weekday. day_of_week: 0=Mon..5=Sat."""
    __tablename__ = "time_slots"
    id: Mapped[int] = mapped_column(primary_key=True)
    day_of_week: Mapped[int] = mapped_column(Integer)
    period_index: Mapped[int] = mapped_column(Integer)  # 0-based ordinal within the day
    start_time: Mapped[str] = mapped_column(String(5))  # "09:00"
    end_time: Mapped[str] = mapped_column(String(5))
    is_preferred: Mapped[bool] = mapped_column(Boolean, default=False)  # good slot for important subjects

    __table_args__ = (UniqueConstraint("day_of_week", "period_index", name="uq_slot"),)


class Availability(Base):
    """Marks a teacher available for a slot. Absence of a row = unavailable if
    the teacher has any availability rows; if none exist the teacher is treated
    as available for all slots."""
    __tablename__ = "availabilities"
    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"))
    time_slot_id: Mapped[int] = mapped_column(ForeignKey("time_slots.id", ondelete="CASCADE"))

    teacher: Mapped[Teacher] = relationship(back_populates="availability")


class TimetableEntry(Base):
    """A locked base-timetable assignment. version groups a generation run."""
    __tablename__ = "timetable_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    time_slot_id: Mapped[int] = mapped_column(ForeignKey("time_slots.id"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    class_section_id: Mapped[int] = mapped_column(ForeignKey("class_sections.id"))
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))

    time_slot: Mapped[TimeSlot] = relationship()
    teacher: Mapped[Teacher] = relationship()
    subject: Mapped[Subject] = relationship()
    class_section: Mapped[ClassSection] = relationship()
    room: Mapped[Room] = relationship()


class Leave(Base):
    __tablename__ = "leaves"
    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), index=True)
    leave_date: Mapped[date] = mapped_column(Date, index=True)
    scope: Mapped[LeaveScope] = mapped_column(Enum(LeaveScope), default=LeaveScope.FULL_DAY)
    reason: Mapped[str | None] = mapped_column(String(400))
    status: Mapped[LeaveStatus] = mapped_column(Enum(LeaveStatus), default=LeaveStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    teacher: Mapped[Teacher] = relationship()
    # For PERIODS scope, the specific slots affected.
    periods: Mapped[list[LeavePeriod]] = relationship(back_populates="leave", cascade="all, delete-orphan")


class LeavePeriod(Base):
    __tablename__ = "leave_periods"
    id: Mapped[int] = mapped_column(primary_key=True)
    leave_id: Mapped[int] = mapped_column(ForeignKey("leaves.id", ondelete="CASCADE"))
    time_slot_id: Mapped[int] = mapped_column(ForeignKey("time_slots.id"))

    leave: Mapped[Leave] = relationship(back_populates="periods")
    time_slot: Mapped[TimeSlot] = relationship()


class Substitution(Base):
    """A daily override: on a specific date, an affected base entry is covered
    (or not) by a substitute teacher."""
    __tablename__ = "substitutions"
    id: Mapped[int] = mapped_column(primary_key=True)
    override_date: Mapped[date] = mapped_column(Date, index=True)
    timetable_entry_id: Mapped[int] = mapped_column(ForeignKey("timetable_entries.id"))
    leave_id: Mapped[int | None] = mapped_column(ForeignKey("leaves.id"))
    absent_teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), index=True)
    substitute_teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), index=True)
    status: Mapped[SubstitutionStatus] = mapped_column(Enum(SubstitutionStatus), default=SubstitutionStatus.ASSIGNED)
    source: Mapped[SubstitutionSource] = mapped_column(Enum(SubstitutionSource), default=SubstitutionSource.AUTO)
    explanation: Mapped[str | None] = mapped_column(String(600))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    timetable_entry: Mapped[TimetableEntry] = relationship()
    absent_teacher: Mapped[Teacher] = relationship(foreign_keys=[absent_teacher_id])
    substitute_teacher: Mapped[Teacher | None] = relationship(foreign_keys=[substitute_teacher_id])


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(String(800))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"))
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
