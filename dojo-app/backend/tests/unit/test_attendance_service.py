"""Unit tests for app.services.attendance_service module."""

import pytest
from fastapi import HTTPException

from app.core.security import get_password_hash
from app.schemas import AttendanceCreate, CheckInQRRequest, CheckInRequest
from app.services.attendance_service import AttendanceService
from tests.unit.conftest import (
    make_attendance,
    make_belt,
    make_event,
    make_event_type,
    make_student,
    make_user,
)


class TestAttendanceServiceGet:
    """Tests for AttendanceService get operations."""

    def test_get_attendance_by_id(self, db_session):
        """Should return attendance by ID."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        user = make_user(db_session)
        event = make_event(db_session, event_type_id=et.id, created_by=user.id)
        student = make_student(db_session, current_belt_id=belt.id)
        db_session.commit()

        attendance = make_attendance(db_session, event_id=event.id, student_id=student.id)
        db_session.commit()

        found = AttendanceService.get_attendance(db_session, attendance.id)
        assert found is not None
        assert found.id == attendance.id

    def test_get_attendance_not_found(self, db_session):
        """Should return None for nonexistent ID."""
        found = AttendanceService.get_attendance(db_session, "nonexistent")
        assert found is None

    def test_get_event_attendances(self, db_session):
        """Should return attendances for an event."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        user = make_user(db_session)
        event = make_event(db_session, event_type_id=et.id, created_by=user.id)
        student = make_student(db_session, current_belt_id=belt.id, registration_number="A001")
        db_session.commit()

        make_attendance(db_session, event_id=event.id, student_id=student.id)
        db_session.commit()

        result = AttendanceService.get_event_attendances(db_session, event.id)
        assert len(result) >= 1
        assert result[0]["student_name"] == student.full_name

    def test_get_student_attendances(self, db_session):
        """Should return attendances for a student."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        user = make_user(db_session)
        event = make_event(db_session, event_type_id=et.id, created_by=user.id)
        student = make_student(db_session, current_belt_id=belt.id)
        db_session.commit()

        make_attendance(db_session, event_id=event.id, student_id=student.id)
        db_session.commit()

        result = AttendanceService.get_student_attendances(db_session, student.id)
        assert len(result) >= 1


class TestAttendanceServiceCheckIn:
    """Tests for AttendanceService.check_in (tablet check-in)."""

    def _setup_event_and_student(self, db_session):
        """Helper to create event and student for check-in tests."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        user = make_user(db_session)
        event = make_event(db_session, event_type_id=et.id, created_by=user.id)
        student = make_student(
            db_session,
            current_belt_id=belt.id,
            registration_number="CHK001",
            pin=get_password_hash("1234"),
        )
        db_session.commit()
        return event, student

    def test_check_in_success(self, db_session):
        """Should successfully check in a student."""
        event, student = self._setup_event_and_student(db_session)

        data = CheckInRequest(
            registration_number="CHK001",
            pin="1234",
            check_in_method="tablet",
        )
        result = AttendanceService.check_in(db_session, data, event.id)
        assert result.student_id == student.id
        assert result.event_id == event.id
        assert result.check_in_method == "tablet"

    def test_check_in_invalid_pin(self, db_session):
        """Should raise 401 for wrong PIN."""
        event, student = self._setup_event_and_student(db_session)

        data = CheckInRequest(
            registration_number="CHK001",
            pin="wrong_pin",
            check_in_method="tablet",
        )
        with pytest.raises(HTTPException) as exc_info:
            AttendanceService.check_in(db_session, data, event.id)
        assert exc_info.value.status_code == 401

    def test_check_in_nonexistent_student(self, db_session):
        """Should raise 404 for nonexistent registration number."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        user = make_user(db_session)
        event = make_event(db_session, event_type_id=et.id, created_by=user.id)
        db_session.commit()

        data = CheckInRequest(
            registration_number="NONEXISTENT",
            pin="1234",
            check_in_method="tablet",
        )
        with pytest.raises(HTTPException) as exc_info:
            AttendanceService.check_in(db_session, data, event.id)
        assert exc_info.value.status_code == 404

    def test_check_in_inactive_student(self, db_session):
        """Should raise 400 for inactive student."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        user = make_user(db_session)
        event = make_event(db_session, event_type_id=et.id, created_by=user.id)
        student = make_student(
            db_session,
            current_belt_id=belt.id,
            registration_number="INACT01",
            pin=get_password_hash("1234"),
            is_active=False,
        )
        db_session.commit()

        data = CheckInRequest(
            registration_number="INACT01",
            pin="1234",
            check_in_method="tablet",
        )
        with pytest.raises(HTTPException) as exc_info:
            AttendanceService.check_in(db_session, data, event.id)
        assert exc_info.value.status_code == 400

    def test_check_in_cancelled_event(self, db_session):
        """Should raise 400 for cancelled event."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        user = make_user(db_session)
        event = make_event(db_session, event_type_id=et.id, created_by=user.id, status="cancelled")
        db_session.commit()

        data = CheckInRequest(
            registration_number="CHK001",
            pin="1234",
            check_in_method="tablet",
        )
        with pytest.raises(HTTPException) as exc_info:
            AttendanceService.check_in(db_session, data, event.id)
        assert exc_info.value.status_code == 400

    def test_check_in_nonexistent_event(self, db_session):
        """Should raise 404 for nonexistent event."""
        data = CheckInRequest(
            registration_number="CHK001",
            pin="1234",
            check_in_method="tablet",
        )
        with pytest.raises(HTTPException) as exc_info:
            AttendanceService.check_in(db_session, data, "nonexistent")
        assert exc_info.value.status_code == 404

    def test_check_in_duplicate_prevention(self, db_session):
        """Should raise 400 for duplicate check-in."""
        event, student = self._setup_event_and_student(db_session)

        data = CheckInRequest(
            registration_number="CHK001",
            pin="1234",
            check_in_method="tablet",
        )
        # First check-in succeeds
        AttendanceService.check_in(db_session, data, event.id)

        # Second check-in should fail
        with pytest.raises(HTTPException) as exc_info:
            AttendanceService.check_in(db_session, data, event.id)
        assert exc_info.value.status_code == 400


class TestAttendanceServiceCheckInQR:
    """Tests for AttendanceService.check_in_qr (QR code check-in)."""

    def test_check_in_qr_success(self, db_session):
        """Should successfully check in via QR code."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        user = make_user(db_session)
        event = make_event(db_session, event_type_id=et.id, created_by=user.id)
        student = make_student(
            db_session,
            current_belt_id=belt.id,
            registration_number="QR001",
            pin=get_password_hash("1234"),
        )
        db_session.commit()

        data = CheckInQRRequest(
            registration_number="QR001",
            pin="1234",
            check_in_token=event.check_in_token,
        )
        result = AttendanceService.check_in_qr(db_session, data)
        assert result.student_id == student.id
        assert result.check_in_method == "qrcode"

    def test_check_in_qr_invalid_token(self, db_session):
        """Should raise 404 for invalid check-in token."""
        data = CheckInQRRequest(
            registration_number="QR001",
            pin="1234",
            check_in_token="invalid-token",
        )
        with pytest.raises(HTTPException) as exc_info:
            AttendanceService.check_in_qr(db_session, data)
        assert exc_info.value.status_code == 404

    def test_check_in_qr_cancelled_event(self, db_session):
        """Should raise 400 for cancelled event via QR."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        user = make_user(db_session)
        event = make_event(db_session, event_type_id=et.id, created_by=user.id, status="cancelled")
        db_session.commit()

        data = CheckInQRRequest(
            registration_number="QR001",
            pin="1234",
            check_in_token=event.check_in_token,
        )
        with pytest.raises(HTTPException) as exc_info:
            AttendanceService.check_in_qr(db_session, data)
        assert exc_info.value.status_code == 400


class TestAttendanceServiceManual:
    """Tests for AttendanceService.create_manual_attendance."""

    def test_manual_attendance_success(self, db_session):
        """Should create attendance manually."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        user = make_user(db_session)
        event = make_event(db_session, event_type_id=et.id, created_by=user.id)
        student = make_student(db_session, current_belt_id=belt.id)
        db_session.commit()

        data = AttendanceCreate(
            event_id=event.id,
            student_id=student.id,
            check_in_method="manual",
            registered_by=user.id,
        )
        result = AttendanceService.create_manual_attendance(db_session, data)
        assert result.student_id == student.id
        assert result.check_in_method == "manual"

    def test_manual_attendance_inactive_student(self, db_session):
        """Should raise 400 for inactive student."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        user = make_user(db_session)
        event = make_event(db_session, event_type_id=et.id, created_by=user.id)
        student = make_student(db_session, current_belt_id=belt.id, is_active=False)
        db_session.commit()

        data = AttendanceCreate(
            event_id=event.id,
            student_id=student.id,
            check_in_method="manual",
        )
        with pytest.raises(HTTPException) as exc_info:
            AttendanceService.create_manual_attendance(db_session, data)
        assert exc_info.value.status_code == 400

    def test_manual_attendance_nonexistent_student(self, db_session):
        """Should raise 404 for nonexistent student."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        user = make_user(db_session)
        event = make_event(db_session, event_type_id=et.id, created_by=user.id)
        db_session.commit()

        data = AttendanceCreate(
            event_id=event.id,
            student_id="nonexistent",
            check_in_method="manual",
        )
        with pytest.raises(HTTPException) as exc_info:
            AttendanceService.create_manual_attendance(db_session, data)
        assert exc_info.value.status_code == 404

    def test_manual_attendance_duplicate_prevention(self, db_session):
        """Should raise 400 for duplicate manual attendance."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        user = make_user(db_session)
        event = make_event(db_session, event_type_id=et.id, created_by=user.id)
        student = make_student(db_session, current_belt_id=belt.id)
        db_session.commit()

        data = AttendanceCreate(
            event_id=event.id,
            student_id=student.id,
            check_in_method="manual",
        )
        # First attendance succeeds
        AttendanceService.create_manual_attendance(db_session, data)

        # Second should fail
        with pytest.raises(HTTPException) as exc_info:
            AttendanceService.create_manual_attendance(db_session, data)
        assert exc_info.value.status_code == 400


class TestAttendanceServiceDelete:
    """Tests for AttendanceService.delete_attendance."""

    def test_delete_attendance(self, db_session):
        """Should delete attendance record."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        user = make_user(db_session)
        event = make_event(db_session, event_type_id=et.id, created_by=user.id)
        student = make_student(db_session, current_belt_id=belt.id)
        db_session.commit()

        attendance = make_attendance(db_session, event_id=event.id, student_id=student.id)
        db_session.commit()
        attendance_id = attendance.id

        AttendanceService.delete_attendance(db_session, attendance_id)
        assert AttendanceService.get_attendance(db_session, attendance_id) is None

    def test_delete_nonexistent_attendance(self, db_session):
        """Should raise 404 for nonexistent attendance."""
        with pytest.raises(HTTPException) as exc_info:
            AttendanceService.delete_attendance(db_session, "nonexistent")
        assert exc_info.value.status_code == 404
