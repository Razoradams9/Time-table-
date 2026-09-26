"""Pydantic schemas (request/response models)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import (
    LeaveScope,
    LeaveStatus,
    Role,
    SubstitutionSource,
    SubstitutionStatus,
)


# ---------- Auth ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    teacher_id: int
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------- Core reference data ----------
class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    department_id: int | None
    importance: int
    is_lab: bool
    periods_per_week: int


class ClassSectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    is_lab: bool
    capacity: int


class TimeSlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    day_of_week: int
    period_index: int
    start_time: str
    end_time: str
    is_preferred: bool


class TeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    role: Role
    department_id: int | None
    max_periods_per_day: int
    is_active: bool


# ---------- Timetable ----------
class TimetableEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    version: int
    is_active: bool
    time_slot: TimeSlotOut
    teacher: TeacherOut
    subject: SubjectOut
    class_section: ClassSectionOut
    room: RoomOut


class GenerationResult(BaseModel):
    success: bool
    version: int | None = None
    entries: int = 0
    message: str
    conflicts: list[str] = []


# ---------- Leaves ----------
class LeaveCreate(BaseModel):
    leave_date: date
    scope: LeaveScope = LeaveScope.FULL_DAY
    reason: str | None = None
    time_slot_ids: list[int] = []  # required when scope == PERIODS


class LeaveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    teacher_id: int
    leave_date: date
    scope: LeaveScope
    reason: str | None
    status: LeaveStatus
    created_at: datetime


# ---------- Substitutions ----------
class SubstitutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    override_date: date
    timetable_entry_id: int
    absent_teacher_id: int
    substitute_teacher_id: int | None
    status: SubstitutionStatus
    source: SubstitutionSource
    explanation: str | None
    created_at: datetime


class SubstitutionDetail(BaseModel):
    id: int
    override_date: date
    status: SubstitutionStatus
    source: SubstitutionSource
    explanation: str | None
    period: str
    day_of_week: int
    subject: str
    class_section: str
    room: str
    absent_teacher: str
    substitute_teacher: str | None


class ManualAssignRequest(BaseModel):
    substitute_teacher_id: int


class Candidate(BaseModel):
    teacher_id: int
    name: str
    score: float
    reason: str


class Suggestion(BaseModel):
    kind: str          # SWAP | MERGE | SELF_STUDY | CANDIDATE
    description: str
    explanation: str
    payload: dict = {}


# ---------- Notifications ----------
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    body: str
    is_read: bool
    created_at: datetime


# ---------- Dashboard / reports ----------
class DashboardSummary(BaseModel):
    date: date
    absent_teachers: list[str]
    covered_periods: int
    uncovered_periods: int
    substitutions: list[SubstitutionDetail]


class FairnessRow(BaseModel):
    teacher_id: int
    name: str
    substitutions_given: int


class LeaveHistoryRow(BaseModel):
    leave_id: int
    leave_date: date
    scope: LeaveScope
    reason: str | None
    status: LeaveStatus


class OverviewStats(BaseModel):
    total_teachers: int
    present_today: int
    absent_today: int
    substitutions_today: int
    uncovered_today: int
    date: date


class ActivityItem(BaseModel):
    id: int
    action: str
    entity: str
    detail: str | None
    actor: str | None
    created_at: datetime
