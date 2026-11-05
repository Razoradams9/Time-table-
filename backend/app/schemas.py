"""Pydantic schemas (request/response models)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import (
    CompensationStatus,
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
    must_change_password: bool = False


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------- Account management ----------
class TeacherCreate(BaseModel):
    name: str
    email: EmailStr
    department_id: int | None = None
    max_periods_per_day: int = 5
    role: Role = Role.TEACHER
    subject_ids: list[int] = []


class TeacherUpdate(BaseModel):
    name: str | None = None
    department_id: int | None = None
    max_periods_per_day: int | None = None
    is_active: bool | None = None
    subject_ids: list[int] | None = None


class TeacherCreated(BaseModel):
    id: int
    name: str
    email: EmailStr
    temp_password: str  # shown once to the HOD to hand over / message


class PasswordReset(BaseModel):
    temp_password: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str


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
    must_change_password: bool = False


# ---------- Timetable ----------
class TimetableEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    version: int
    is_active: bool
    is_double: bool = False
    block_id: str | None = None
    time_slot: TimeSlotOut
    teacher: TeacherOut
    co_teacher: TeacherOut | None = None
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
    period_index: int
    time_slot_id: int
    subject: str
    class_section: str
    class_section_id: int
    room: str
    absent_teacher: str
    absent_teacher_id: int
    substitute_teacher: str | None
    substitute_teacher_id: int | None


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


class WorkloadDay(BaseModel):
    day_of_week: int
    day_name: str
    periods: int
    hours: float


class WorkloadRow(BaseModel):
    teacher_id: int
    name: str
    role: Role
    scheduled_periods_per_week: int
    scheduled_hours_per_week: float
    scheduled_hours_in_range: float
    hours_substituted_for_others: float
    periods_substituted_for_others: int
    hours_given_up: float
    periods_given_up: int
    uncovered_hours: float
    net_hours_in_range: float
    daily: list[WorkloadDay]


class WorkloadReport(BaseModel):
    start: date
    end: date
    teaching_days: int
    formula: str
    rows: list[WorkloadRow]


class CourseSlot(BaseModel):
    day_of_week: int
    day_name: str
    period_label: str
    start_time: str
    end_time: str
    periods: int
    is_lab: bool
    room: str


class CourseOut(BaseModel):
    subject_id: int
    subject: str
    subject_code: str
    class_section_id: int
    class_section: str
    role_in_course: str
    lead_teacher: str
    co_teachers: list[str]
    periods_per_week: int
    hours_per_week: float
    lecture_periods: int
    lab_periods: int
    lab_blocks: int
    is_lab: bool
    schedule: list[CourseSlot]


class TeacherCourses(BaseModel):
    teacher_id: int
    name: str
    role: Role
    total_courses: int
    total_periods_per_week: int
    total_hours_per_week: float
    lecture_periods: int
    lab_periods: int
    courses: list[CourseOut]


class CoursesReport(BaseModel):
    teachers: list[TeacherCourses]


# ---------- Compensation (make-up classes) ----------
class CompensationOut(BaseModel):
    id: int
    leave_id: int | None
    substitution_id: int | None
    teacher_id: int
    teacher: str
    subject: str
    class_section: str
    class_section_id: int
    is_lab: bool
    missed_date: date
    missed_period: str
    missed_day_of_week: int
    periods: int
    proposed_date: date | None
    proposed_day_of_week: int | None
    proposed_period: str | None
    proposed_start_time: str | None
    proposed_end_time: str | None
    proposed_time_slot_id: int | None
    proposed_time_slot2_id: int | None
    room: str | None
    room_id: int | None
    status: CompensationStatus
    notes: str | None
    created_at: datetime
    can_complete: bool


class CompensationSlotRequest(BaseModel):
    date: date
    time_slot_id: int
    time_slot2_id: int | None = None
    room_id: int | None = None


class CompensationSuggestionOut(BaseModel):
    date: date
    day_name: str
    time_slot_id: int
    time_slot2_id: int | None
    period_label: str
    start_time: str
    end_time: str
    room_id: int
    room: str
    week_offset: int
    teacher_load_that_day: int
    reason: str


class CompensationSummary(BaseModel):
    owed: int
    proposed: int
    scheduled: int
    completed: int
    cancelled: int


class BackfillResult(BaseModel):
    created: int
    periods: int
    skipped: int


class CompensationCalendarItem(BaseModel):
    id: int
    teacher_id: int
    teacher: str
    class_section_id: int
    class_section: str
    subject: str
    date: date
    day_of_week: int
    period_indexes: list[int]
    periods: int
    room: str | None
    status: CompensationStatus
    is_lab: bool


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
