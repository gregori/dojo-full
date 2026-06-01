from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import Attendance, Student, Event
from app.schemas import AttendanceCreate, CheckInRequest, CheckInQRRequest
from app.core.security import verify_password
from app.services.student_service import StudentService
from app.services.event_service import EventService


class AttendanceService:
    @staticmethod
    def get_attendance(db: Session, attendance_id: str) -> Optional[Attendance]:
        return db.query(Attendance).filter(Attendance.id == attendance_id).first()

    @staticmethod
    def get_event_attendances(db: Session, event_id: str) -> list[Attendance]:
        attendances = db.query(Attendance).filter(Attendance.event_id == event_id).all()
        result = []
        for a in attendances:
            attendance_dict = {
                "id": a.id,
                "event_id": a.event_id,
                "student_id": a.student_id,
                "student_name": a.student.full_name if a.student else None,
                "check_in_method": a.check_in_method,
                "check_in_at": a.check_in_at,
                "registered_by": a.registered_by,
                "created_at": a.created_at,
            }
            result.append(attendance_dict)
        return result

    @staticmethod
    def get_student_attendances(db: Session, student_id: str) -> list[Attendance]:
        return db.query(Attendance).filter(Attendance.student_id == student_id).all()

    @staticmethod
    def check_in(db: Session, check_in_data: CheckInRequest, event_id: str, registered_by: Optional[str] = None) -> Attendance:
        """Process check-in for a student."""
        event = EventService.get_event(db, event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        if event.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event is cancelled"
            )

        student = StudentService.get_student_by_registration(db, check_in_data.registration_number)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        if not student.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student is inactive"
            )
        
        # Verify PIN
        if not verify_password(check_in_data.pin, student.pin):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid PIN"
            )
        
        # Check if already checked in
        existing = db.query(Attendance).filter(
            Attendance.student_id == student.id,
            Attendance.event_id == event_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attendance already recorded"
            )
        
        # Create attendance
        attendance = Attendance(
            event_id=event_id,
            student_id=student.id,
            check_in_method=check_in_data.check_in_method,
            check_in_at=datetime.now(timezone.utc),
            registered_by=registered_by,
        )
        db.add(attendance)
        db.commit()
        db.refresh(attendance)
        return attendance

    @staticmethod
    def check_in_qr(db: Session, check_in_data: CheckInQRRequest) -> Attendance:
        """Process check-in via QR code."""
        event = EventService.get_event_by_token(db, check_in_data.check_in_token)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid check-in token"
            )
        
        if event.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event is cancelled"
            )
        
        # Convert to regular check-in
        regular_check_in = CheckInRequest(
            registration_number=check_in_data.registration_number,
            pin=check_in_data.pin,
            check_in_method="qrcode"
        )
        
        return AttendanceService.check_in(db, regular_check_in, event.id)

    @staticmethod
    def create_manual_attendance(db: Session, attendance_data: AttendanceCreate) -> Attendance:
        """Create attendance manually (by instructor/admin)."""
        student = db.query(Student).filter(Student.id == attendance_data.student_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )

        if not student.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student is inactive"
            )

        existing = db.query(Attendance).filter(
            Attendance.student_id == attendance_data.student_id,
            Attendance.event_id == attendance_data.event_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attendance already recorded for this student at this event"
            )

        attendance = Attendance(
            event_id=attendance_data.event_id,
            student_id=attendance_data.student_id,
            check_in_method=attendance_data.check_in_method,
            check_in_at=datetime.now(timezone.utc),
            registered_by=attendance_data.registered_by,
        )
        db.add(attendance)
        db.commit()
        db.refresh(attendance)
        return attendance

    @staticmethod
    def delete_attendance(db: Session, attendance_id: str) -> None:
        attendance = AttendanceService.get_attendance(db, attendance_id)
        if not attendance:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance not found")
        db.delete(attendance)
        db.commit()
