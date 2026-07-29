"""Instructor/admin-only endpoints for belt-exam, attendance, and financial reports (REP-01-REP-05).

Each report endpoint supports ``?format=json|pdf|csv`` (default ``json``)
rather than tripling the route count: the json branch returns a typed
Pydantic response, and the pdf/csv branches return a plain ``Response`` with
``Content-Disposition: attachment``, mirroring ``contracts.py``'s
``download_contract`` endpoint exactly.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_instructor_or_admin
from app.schemas.report import (
    BeltExamReportResponse,
    ClassAttendanceReportResponse,
    FinancialReportResponse,
    StudentAttendanceReportResponse,
)
from app.services.report_export_service import ReportExportService
from app.services.report_service import ReportService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

VALID_FORMATS = {"json", "pdf", "csv"}


def _validate_format(report_format: str) -> None:
    if report_format not in VALID_FORMATS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid format")


def _export(content: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _render(
    report_format: str, title: str, sections: list[tuple[str, list[str], list[list[str]]]], filename_stem: str
) -> Response:
    if report_format == "pdf":
        content = ReportExportService.render_pdf_table(title, sections)
        return _export(content, "application/pdf", f"{filename_stem}.pdf")
    content = ReportExportService.render_csv(sections)
    return _export(content, "text/csv", f"{filename_stem}.csv")


def _belt_exam_sections(report: dict) -> list[tuple[str, list[str], list[list[str]]]]:
    headers = ["Data", "Faixa Alvo", "Papel", "Status", "Promovido em", "Faixa Promovida"]
    rows = [
        [
            participation["exam_date"].strftime("%d/%m/%Y"),
            participation["target_belt_name"],
            "Candidato" if participation["role"] == "candidate" else "Uke",
            participation["status"],
            participation["promoted_at"].strftime("%d/%m/%Y") if participation["promoted_at"] else "",
            participation["promoted_belt_name"] or "",
        ]
        for participation in report["participations"]
    ]
    return [(f"Exame de Faixa - {report['student_name']}", headers, rows)]


def _student_attendance_sections(report: dict) -> list[tuple[str, list[str], list[list[str]]]]:
    headers = ["Evento", "Tipo", "Data/Hora", "Método"]
    rows = [
        [
            attendance["event_title"],
            attendance["event_type_name"],
            attendance["check_in_at"].strftime("%d/%m/%Y %H:%M"),
            attendance["check_in_method"],
        ]
        for attendance in report["attendances"]
    ]
    title = f"Presenças - {report['student_name']} (Total: {report['total_attendances']})"
    return [(title, headers, rows)]


def _class_attendance_sections(report: dict) -> list[tuple[str, list[str], list[list[str]]]]:
    events_headers = ["Evento", "Data", "Presenças"]
    events_rows = [
        [event["event_title"], event["start_datetime"].strftime("%d/%m/%Y %H:%M"), str(event["attendance_count"])]
        for event in report["events"]
    ]
    roster_headers = ["Aluno", "Total de Presenças"]
    roster_rows = [
        [roster_item["student_name"], str(roster_item["total_attendances"])] for roster_item in report["roster"]
    ]
    return [
        (f"Eventos - {report['event_type_name']}", events_headers, events_rows),
        (f"Roster - {report['event_type_name']}", roster_headers, roster_rows),
    ]


def _financial_sections(report: dict) -> list[tuple[str, list[str], list[list[str]]]]:
    payments_headers = ["Aluno", "Valor", "Data", "Método"]
    payments_rows = [
        [
            payment["student_name"],
            f"R$ {payment['amount']:,.2f}",
            payment["payment_date"].strftime("%d/%m/%Y"),
            payment["method"] or "",
        ]
        for payment in report["payments"]
    ]

    delinquency_headers = ["Aluno", "Matrícula", "Valor Devido", "Vencido desde"]
    delinquency_rows = [
        [
            item["student_name"],
            item["registration_number"],
            f"R$ {item['amount_owed']:,.2f}",
            item["oldest_overdue_due_date"].strftime("%d/%m/%Y") if item["oldest_overdue_due_date"] else "",
        ]
        for item in report["delinquency"]
    ]

    projection = report["projection"]
    projection_headers = ["Total Mensal", "Meses", "Total Projetado"]
    projection_rows = [
        [
            f"R$ {projection['monthly_total']:,.2f}",
            str(projection["months_ahead"]),
            f"R$ {projection['projected_total']:,.2f}",
        ]
    ]

    return [
        ("Pagamentos", payments_headers, payments_rows),
        ("Inadimplência", delinquency_headers, delinquency_rows),
        ("Projeção", projection_headers, projection_rows),
    ]


@router.get("/belt-exams/{student_id}")
def belt_exam_report(
    student_id: str,
    format: str = "json",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """REP-01: a student's belt-exam participation history and resulting promotions."""
    _validate_format(format)
    report = ReportService.get_belt_exam_report(db, student_id)
    if format == "json":
        return BeltExamReportResponse(**report)
    return _render(
        format,
        f"Exame de Faixa - {report['student_name']}",
        _belt_exam_sections(report),
        f"exame-faixa-{student_id}",
    )


@router.get("/attendance/student/{student_id}")
def student_attendance_report(
    student_id: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    format: str = "json",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """REP-02: a student's attendance report over a date range (defaults to the current month)."""
    _validate_format(format)
    report = ReportService.get_student_attendance_report(db, student_id, start_date, end_date)
    if format == "json":
        return StudentAttendanceReportResponse(**report)
    return _render(
        format,
        f"Presenças - {report['student_name']}",
        _student_attendance_sections(report),
        f"presencas-aluno-{student_id}",
    )


@router.get("/attendance/class")
def class_attendance_report(
    event_type_id: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    format: str = "json",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """REP-03: a class/period attendance report scoped to an ``EventType`` and date range."""
    _validate_format(format)
    report = ReportService.get_class_attendance_report(db, event_type_id, start_date, end_date)
    if format == "json":
        return ClassAttendanceReportResponse(**report)
    return _render(
        format,
        f"Presenças - {report['event_type_name']}",
        _class_attendance_sections(report),
        f"presencas-turma-{event_type_id}",
    )


@router.get("/finance")
def financial_report(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    months_ahead: int = 3,
    format: str = "json",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """REP-04: payments, delinquency, and a revenue projection over a date range."""
    _validate_format(format)
    report = ReportService.get_financial_report(db, start_date, end_date, months_ahead)
    if format == "json":
        return FinancialReportResponse(**report)
    return _render(format, "Relatório Financeiro", _financial_sections(report), "relatorio-financeiro")
