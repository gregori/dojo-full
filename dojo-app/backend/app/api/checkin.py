from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.rate_limiter import checkin_rate_limiter
from app.schemas import (
    CheckInRequest, CheckInQRRequest, CheckInResponse,
    AttendanceCreate, AttendanceResponse
)
from app.services import AttendanceService, StudentService
from app.dependencies.auth import get_current_user, get_current_instructor_or_admin

router = APIRouter(prefix="/api/v1/checkin", tags=["check-in"])


@router.post("/tablet/{event_id}", response_model=CheckInResponse)
def check_in_tablet(
    event_id: str,
    check_in_data: CheckInRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Check in via tablet (no auth required - public endpoint)."""
    rate_limit_key = f"{request.client.host}:{check_in_data.registration_number}"
    checkin_rate_limiter.check_rate_limit(rate_limit_key)
    
    attendance = AttendanceService.check_in(db, check_in_data, event_id)
    student = attendance.student
    event = attendance.event
    
    # Get progress
    progress = StudentService.get_student_progress(db, student.id)
    
    return CheckInResponse(
        status="success",
        message=f"Presença registrada! Bem-vindo, {student.full_name}",
        student_name=student.full_name,
        event_title=event.title,
        progress=progress
    )


@router.post("/qr", response_model=CheckInResponse)
def check_in_qr(
    check_in_data: CheckInQRRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Check in via QR code (no auth required - public endpoint)."""
    rate_limit_key = f"{request.client.host}:{check_in_data.registration_number}"
    checkin_rate_limiter.check_rate_limit(rate_limit_key)
    
    attendance = AttendanceService.check_in_qr(db, check_in_data)
    student = attendance.student
    event = attendance.event
    
    # Get progress
    progress = StudentService.get_student_progress(db, student.id)
    
    return CheckInResponse(
        status="success",
        message=f"Presença registrada! Bem-vindo, {student.full_name}",
        student_name=student.full_name,
        event_title=event.title,
        progress=progress
    )


@router.post("/manual", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
def check_in_manual(
    attendance_data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_instructor_or_admin)
):
    """Manually register attendance (instructor/admin only)."""
    attendance_data.registered_by = current_user.id
    return AttendanceService.create_manual_attendance(db, attendance_data)


@router.get("/event/{event_id}", response_model=List[AttendanceResponse])
def list_event_attendances(
    event_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_instructor_or_admin)
):
    """List all attendances for an event."""
    return AttendanceService.get_event_attendances(db, event_id)


@router.delete("/{attendance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance(
    attendance_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_instructor_or_admin)
):
    """Delete an attendance record."""
    AttendanceService.delete_attendance(db, attendance_id)
