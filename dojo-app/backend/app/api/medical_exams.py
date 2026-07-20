"""Public and instructor-only endpoints for medical exam records."""

from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limiter import medical_exam_rate_limiter
from app.dependencies.auth import get_current_instructor_or_admin
from app.schemas import (
    MedicalExamDashboardItem,
    MedicalExamPublicResponse,
    MedicalExamResponse,
    MedicalExamStatus,
)
from app.services import MedicalExamService, StudentService

router = APIRouter(prefix="/api/v1/medical-exams", tags=["medical-exams"])
GENERIC_MESSAGE = "If the supplied details are valid, your request has been processed."


def _rate_limit(request: Request, registration_number: str) -> None:
    client_ip = request.client.host if request.client else "unknown"
    medical_exam_rate_limiter.check_rate_limit(f"ip:{client_ip}")
    medical_exam_rate_limiter.check_rate_limit(f"registration:{registration_number}")


@router.post("/public/submit", response_model=MedicalExamPublicResponse)
def submit_medical_exam(
    request: Request,
    registration_number: str = Form(...),
    pin: str = Form(...),
    exam_date: date = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Self-submit a medical exam via registration number + PIN, without disclosing credential validity."""
    _rate_limit(request, registration_number)
    student = MedicalExamService.authenticate_student(db, registration_number, pin)
    if not student:
        return MedicalExamPublicResponse(status="accepted", message=GENERIC_MESSAGE)
    MedicalExamService.record_exam(
        db, student, exam_date, file, uploaded_by_user_id=None, uploaded_by_student_self=True
    )
    return MedicalExamPublicResponse(status="accepted", message=GENERIC_MESSAGE)


@router.get("/dashboard", response_model=list[MedicalExamDashboardItem])
def get_medical_exam_dashboard(db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)):
    """List active students whose medical exam status is vencendo or vencido (instructor/admin only)."""
    return MedicalExamService.get_dashboard(db)


@router.post("/students/{student_id}", response_model=MedicalExamResponse, status_code=status.HTTP_201_CREATED)
def record_medical_exam(
    student_id: str,
    exam_date: date = Form(...),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """Record a medical exam for a student, superseding any prior active record (instructor/admin only)."""
    student = StudentService.get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return MedicalExamService.record_exam(
        db, student, exam_date, file, uploaded_by_user_id=current_user.id, uploaded_by_student_self=False
    )


@router.get("/students/{student_id}/status", response_model=MedicalExamStatus)
def get_medical_exam_status(
    student_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """Return the computed medical-exam status for a student (instructor/admin only)."""
    return MedicalExamService.get_status(db, student_id)


@router.get("/students/{student_id}", response_model=list[MedicalExamResponse])
def list_medical_exams(
    student_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """List a student's medical exam history, most recent first (instructor/admin only)."""
    return MedicalExamService.get_history(db, student_id)
