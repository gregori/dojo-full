"""Business rules for pre-check-ins, which remain separate from attendance."""

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models import Event, PreCheckIn, Student
from app.services.event_service import EventService
from app.services.student_service import StudentService

PRE_CHECKIN_CUTOFF = timedelta(hours=1)


class PreCheckInService:
    """Create, cancel, list, and convert pre-check-ins according to event rules."""

    @staticmethod
    def authenticate_student(db: Session, registration_number: str, pin: str) -> Student | None:
        """Return the active student for valid public credentials, otherwise ``None``."""
        student = StudentService.get_student_by_registration(db, registration_number)
        if not student or not student.is_active or not verify_password(pin, student.pin):
            return None
        return student

    @staticmethod
    def _get_event_for_change(db: Session, event_id: str) -> Event:
        event = EventService.get_event(db, event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        if event.status != "scheduled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Pre-check-in is unavailable for this event"
            )

        start = event.start_datetime
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if datetime.now(UTC) >= start - PRE_CHECKIN_CUTOFF:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pre-check-in is closed for this event")
        return event

    @staticmethod
    def _validate_eligibility(event: Event, student: Student) -> None:
        if not event.minimum_belt_id:
            return
        minimum_belt = event.minimum_belt
        if not minimum_belt or student.current_belt.sort_order < minimum_belt.sort_order:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student is not eligible for this event")

    @staticmethod
    def confirm(db: Session, event_id: str, student: Student) -> PreCheckIn:
        """Confirm a student's intent to attend an eligible, open event."""
        event = PreCheckInService._get_event_for_change(db, event_id)
        PreCheckInService._validate_eligibility(event, student)
        record = (
            db.query(PreCheckIn).filter(PreCheckIn.event_id == event_id, PreCheckIn.student_id == student.id).first()
        )
        now = datetime.now(UTC)
        if record and record.status == "converted":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pre-check-in has already been converted")
        if record:
            record.status = "confirmed"
            record.confirmed_at = now
            record.cancelled_at = None
        else:
            record = PreCheckIn(event_id=event_id, student_id=student.id, status="confirmed", confirmed_at=now)
            db.add(record)
        try:
            db.commit()
        except IntegrityError:
            # A concurrent confirmation may have created the same unique record.
            db.rollback()
            record = (
                db.query(PreCheckIn)
                .filter(PreCheckIn.event_id == event_id, PreCheckIn.student_id == student.id)
                .first()
            )
            if not record or record.status == "converted":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to confirm pre-check-in")
        db.refresh(record)
        return record

    @staticmethod
    def cancel(db: Session, event_id: str, student: Student) -> PreCheckIn | None:
        """Cancel an existing confirmation without revealing whether one existed."""
        PreCheckInService._get_event_for_change(db, event_id)
        record = (
            db.query(PreCheckIn).filter(PreCheckIn.event_id == event_id, PreCheckIn.student_id == student.id).first()
        )
        if record and record.status == "confirmed":
            record.status = "cancelled"
            record.cancelled_at = datetime.now(UTC)
            db.commit()
            db.refresh(record)
        return record

    @staticmethod
    def get_confirmed_roster(db: Session, event_id: str) -> list[dict]:
        """Return confirmed records and student identity fields for authorized staff."""
        return [
            {
                "id": record.id,
                "event_id": record.event_id,
                "student_id": record.student_id,
                "status": record.status,
                "confirmed_at": record.confirmed_at,
                "cancelled_at": record.cancelled_at,
                "converted_at": record.converted_at,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
                "student_name": record.student.full_name,
                "registration_number": record.student.registration_number,
            }
            for record in (
                db.query(PreCheckIn).filter(PreCheckIn.event_id == event_id, PreCheckIn.status == "confirmed").all()
            )
        ]

    @staticmethod
    def confirmed_count(db: Session, event_id: str) -> int:
        """Count confirmed, unconverted pre-check-ins for an event."""
        return db.query(PreCheckIn).filter(PreCheckIn.event_id == event_id, PreCheckIn.status == "confirmed").count()

    @staticmethod
    def get_public_events(db: Session) -> list[Event]:
        """List future scheduled events still open for public pre-check-in."""
        cutoff = datetime.now(UTC) + PRE_CHECKIN_CUTOFF
        return (
            db.query(Event)
            .filter(Event.status == "scheduled", Event.start_datetime > cutoff)
            .order_by(Event.start_datetime.asc())
            .all()
        )

    @staticmethod
    def convert_for_attendance(db: Session, event_id: str, student_id: str) -> None:
        """Mark a valid confirmation as converted in the same transaction as attendance."""
        record = (
            db.query(PreCheckIn)
            .filter(
                PreCheckIn.event_id == event_id,
                PreCheckIn.student_id == student_id,
                PreCheckIn.status == "confirmed",
            )
            .first()
        )
        if record:
            record.status = "converted"
            record.converted_at = datetime.now(UTC)
