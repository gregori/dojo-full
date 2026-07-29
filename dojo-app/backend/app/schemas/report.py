"""Response schemas for the instructor/admin reports (REP-01-REP-04)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.mensalidade import OverdueDashboardItem


class BeltExamParticipationItem(BaseModel):
    """One exam participation row, plus the resulting promotion, if any."""

    exam_id: str
    exam_date: datetime
    target_belt_name: str
    role: str
    status: str
    override_eligibility: bool
    override_reason: str | None = None
    promoted_at: datetime | None = None
    promoted_belt_name: str | None = None


class BeltExamReportResponse(BaseModel):
    """REP-01: a student's full belt-exam participation history."""

    student_id: str
    student_name: str
    participations: list[BeltExamParticipationItem]


class AttendanceItem(BaseModel):
    """One attendance row in a student's attendance report."""

    event_title: str
    event_type_name: str
    check_in_at: datetime
    check_in_method: str


class StudentAttendanceReportResponse(BaseModel):
    """REP-02: a student's attendance in a date range, plus a total count."""

    student_id: str
    student_name: str
    total_attendances: int
    attendances: list[AttendanceItem]


class ClassEventCount(BaseModel):
    """One event's attendance count in a class attendance report."""

    event_id: str
    event_title: str
    start_datetime: datetime
    attendance_count: int


class ClassRosterItem(BaseModel):
    """One student's attendance total in a class attendance report's roster."""

    student_id: str
    student_name: str
    total_attendances: int


class ClassAttendanceReportResponse(BaseModel):
    """REP-03: per-event counts and a per-student roster for one ``EventType``."""

    event_type_id: str
    event_type_name: str
    events: list[ClassEventCount]
    roster: list[ClassRosterItem]


class FinancialPaymentItem(BaseModel):
    """One payment row in a financial report."""

    id: str
    student_id: str
    student_name: str
    amount: Decimal
    payment_date: datetime
    method: str | None = None


class FinancialProjection(BaseModel):
    """REP-04's revenue projection: sum of active-student prices times ``months_ahead``."""

    monthly_total: Decimal
    months_ahead: int
    projected_total: Decimal


class FinancialReportResponse(BaseModel):
    """REP-04: payments, delinquency, and a revenue projection in one report."""

    payments: list[FinancialPaymentItem]
    delinquency: list[OverdueDashboardItem]
    projection: FinancialProjection
