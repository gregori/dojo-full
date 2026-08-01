"""Identify students, create idempotent notifications, and serve/read history."""

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models import Notification, PushSubscription, Student
from app.services.student_service import StudentService


class NotificationService:
    @staticmethod
    def authenticate_student(db: Session, registration_number: str, pin: str) -> Student | None:
        """Return the active student for valid public credentials, otherwise ``None``.

        Identical idiom to PreCheckInService/MedicalExamService's own
        authenticate_student (a third, deliberate copy -- see plan.md Autocritica).
        """
        student = StudentService.get_student_by_registration(db, registration_number)
        if not student or not student.is_active or not verify_password(pin, student.pin):
            return None
        return student

    @staticmethod
    def create_if_new(
        db: Session, student_id: str, notification_type: str, reference_id: str, message: str
    ) -> Notification | None:
        """Insert a Notification, or return None if this occurrence already fired (NH-06)."""
        notification = Notification(
            student_id=student_id, notification_type=notification_type, reference_id=reference_id, message=message
        )
        db.add(notification)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return None
        db.refresh(notification)
        return notification

    @staticmethod
    def add_subscription(db: Session, student_id: str, endpoint: str, p256dh: str, auth: str) -> PushSubscription:
        subscription = PushSubscription(student_id=student_id, endpoint=endpoint, p256dh_key=p256dh, auth_key=auth)
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription

    @staticmethod
    def get_history(db: Session, student_id: str) -> list[Notification]:
        return (
            db.query(Notification)
            .filter(Notification.student_id == student_id)
            .order_by(Notification.created_at.desc())
            .all()
        )

    @staticmethod
    def mark_read(db: Session, notification_id: str, student_id: str) -> Notification | None:
        """Mark read, scoped to the authenticated student_id (NH-08 cross-device persistence).

        Scoping by student_id (not just notification_id) prevents one student's
        credentials from marking another student's notification read -- a real
        authorization boundary given there is no session/login (mirrors how
        PreCheckInService.cancel always scopes by the authenticated student).
        """
        notification = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.student_id == student_id)
            .first()
        )
        if not notification:
            return None
        if notification.read_at is None:
            notification.read_at = datetime.now(UTC)
            db.commit()
            db.refresh(notification)
        return notification
