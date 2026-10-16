"""HOD dashboard, fairness/leave reports, and exports (Requirement 7)."""
from __future__ import annotations

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AuditLog,
    Leave,
    LeaveStatus,
    Role,
    Substitution,
    SubstitutionStatus,
    Teacher,
)
from app.schemas import (
    ActivityItem,
    DashboardSummary,
    FairnessRow,
    LeaveHistoryRow,
    OverviewStats,
)
from app.security import require_hod
from app.routers.substitutions import to_detail

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=OverviewStats)
def overview(on: date | None = None, db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    d = on or date.today()
    total_teachers = db.scalar(
        select(func.count(Teacher.id)).where(Teacher.is_active.is_(True), Teacher.role == Role.TEACHER)
    ) or 0
    absent_ids = set(
        db.scalars(
            select(Leave.teacher_id).where(
                Leave.leave_date == d, Leave.status == LeaveStatus.ACTIVE
            )
        ).all()
    )
    absent_today = len(absent_ids)
    subs_today = db.scalar(
        select(func.count(Substitution.id)).where(
            Substitution.override_date == d,
            Substitution.status != SubstitutionStatus.CANCELLED,
        )
    ) or 0
    uncovered_today = db.scalar(
        select(func.count(Substitution.id)).where(
            Substitution.override_date == d,
            Substitution.status == SubstitutionStatus.UNCOVERED,
        )
    ) or 0
    return OverviewStats(
        total_teachers=total_teachers,
        present_today=max(0, total_teachers - absent_today),
        absent_today=absent_today,
        substitutions_today=subs_today,
        uncovered_today=uncovered_today,
        date=d,
    )


@router.get("/activity", response_model=list[ActivityItem])
def activity(limit: int = 10, db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    rows = db.scalars(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    ).all()
    names = {t.id: t.name for t in db.scalars(select(Teacher)).all()}
    return [
        ActivityItem(
            id=r.id,
            action=r.action,
            entity=r.entity,
            detail=r.detail,
            actor=names.get(r.actor_id) if r.actor_id else None,
            created_at=r.created_at,
        )
        for r in rows
    ]


def _fairness_rows(db: Session, start: date, end: date) -> list[FairnessRow]:
    counts = dict(
        db.execute(
            select(Substitution.substitute_teacher_id, func.count(Substitution.id))
            .where(
                Substitution.override_date >= start,
                Substitution.override_date <= end,
                Substitution.status == SubstitutionStatus.ASSIGNED,
                Substitution.substitute_teacher_id.is_not(None),
            )
            .group_by(Substitution.substitute_teacher_id)
        ).all()
    )
    rows: list[FairnessRow] = []
    for t in db.scalars(select(Teacher)).all():
        rows.append(FairnessRow(teacher_id=t.id, name=t.name, substitutions_given=counts.get(t.id, 0)))
    rows.sort(key=lambda r: r.substitutions_given, reverse=True)
    return rows


@router.get("/summary", response_model=DashboardSummary)
def summary(on: date | None = None, db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    d = on or date.today()
    subs = db.scalars(
        select(Substitution).where(
            Substitution.override_date == d,
            Substitution.status != SubstitutionStatus.CANCELLED,
        )
    ).all()
    details = [to_detail(s) for s in subs]
    covered = sum(1 for s in subs if s.status == SubstitutionStatus.ASSIGNED)
    uncovered = sum(1 for s in subs if s.status == SubstitutionStatus.UNCOVERED)
    absent = sorted({s.absent_teacher.name for s in subs})
    return DashboardSummary(
        date=d,
        absent_teachers=absent,
        covered_periods=covered,
        uncovered_periods=uncovered,
        substitutions=details,
    )


@router.get("/fairness", response_model=list[FairnessRow])
def fairness(start: date, end: date, db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    return _fairness_rows(db, start, end)


@router.get("/leave-history/{teacher_id}", response_model=list[LeaveHistoryRow])
def leave_history(teacher_id: int, db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    leaves = db.scalars(
        select(Leave).where(Leave.teacher_id == teacher_id).order_by(Leave.leave_date.desc())
    ).all()
    return [
        LeaveHistoryRow(
            leave_id=lv.id, leave_date=lv.leave_date, scope=lv.scope, reason=lv.reason, status=lv.status
        )
        for lv in leaves
    ]


@router.get("/export/fairness.csv")
def export_fairness_csv(start: date, end: date, db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    rows = _fairness_rows(db, start, end)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Teacher ID", "Name", "Substitutions Given", "From", "To"])
    for r in rows:
        writer.writerow([r.teacher_id, r.name, r.substitutions_given, start, end])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=fairness_{start}_{end}.csv"},
    )


@router.get("/export/fairness.pdf")
def export_fairness_pdf(start: date, end: date, db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    rows = _fairness_rows(db, start, end)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Substitution Fairness Report", styles["Title"]),
        Paragraph(f"Period: {start} to {end}", styles["Normal"]),
        Spacer(1, 12),
    ]
    data = [["Teacher", "Substitutions Given"]] + [[r.name, str(r.substitutions_given)] for r in rows]
    table = Table(data, colWidths=[320, 160])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=fairness_{start}_{end}.pdf"},
    )
