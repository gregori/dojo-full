"""Unit tests for app.services.student_service module."""
import pytest
from datetime import datetime, timezone
from fastapi import HTTPException

from app.services.student_service import StudentService
from app.schemas import StudentCreate, StudentUpdate
from app.core.security import get_password_hash, verify_password
from tests.unit.conftest import (
    make_belt, make_student, make_event_type, make_event, make_user,
    make_attendance, make_belt_requirement, make_belt_promotion,
    make_dojo, make_organization, make_exam,
)


class TestStudentServiceGet:
    """Tests for StudentService get operations."""

    def test_get_student_by_id(self, db_session):
        """Should return student by ID."""
        belt = make_belt(db_session)
        student = make_student(db_session, current_belt_id=belt.id)
        db_session.commit()

        found = StudentService.get_student(db_session, student.id)
        assert found is not None
        assert found.id == student.id

    def test_get_student_not_found(self, db_session):
        """Should return None for nonexistent ID."""
        found = StudentService.get_student(db_session, "nonexistent-id")
        assert found is None

    def test_get_student_by_registration(self, db_session):
        """Should return student by registration number."""
        belt = make_belt(db_session)
        student = make_student(db_session, registration_number="0012501", current_belt_id=belt.id)
        db_session.commit()

        found = StudentService.get_student_by_registration(db_session, "0012501")
        assert found is not None
        assert found.registration_number == "0012501"

    def test_get_students_with_category_filter(self, db_session):
        """Should filter students by category."""
        belt = make_belt(db_session)
        make_student(db_session, registration_number="A001", category="adult", current_belt_id=belt.id)
        make_student(db_session, registration_number="C001", category="child", current_belt_id=belt.id)
        db_session.commit()

        adults = StudentService.get_students(db_session, category="adult")
        assert all(s.category == "adult" for s in adults)

    def test_get_students_with_active_filter(self, db_session):
        """Should filter students by active status."""
        belt = make_belt(db_session)
        make_student(db_session, registration_number="A001", is_active=True, current_belt_id=belt.id)
        make_student(db_session, registration_number="A002", is_active=False, current_belt_id=belt.id)
        db_session.commit()

        active = StudentService.get_students(db_session, is_active=True)
        assert all(s.is_active for s in active)


class TestStudentServiceCreate:
    """Tests for StudentService.create_student."""

    def test_create_student_auto_registration(self, db_session):
        """Should auto-generate registration number when not provided."""
        belt = make_belt(db_session)
        db_session.commit()

        data = StudentCreate(
            full_name="New Student",
            category="adult",
            current_belt_id=belt.id,
            pin="1234",
        )
        student = StudentService.create_student(db_session, data)
        assert student.registration_number is not None
        assert len(student.registration_number) > 0

    def test_create_student_with_custom_registration(self, db_session):
        """Should use provided registration number."""
        belt = make_belt(db_session)
        db_session.commit()

        data = StudentCreate(
            full_name="Custom Reg Student",
            category="adult",
            current_belt_id=belt.id,
            pin="1234",
            registration_number="CUSTOM001",
        )
        student = StudentService.create_student(db_session, data)
        assert student.registration_number == "CUSTOM001"

    def test_create_student_hashes_pin(self, db_session):
        """Should hash the PIN on creation."""
        belt = make_belt(db_session)
        db_session.commit()

        data = StudentCreate(
            full_name="Pin Student",
            category="adult",
            current_belt_id=belt.id,
            pin="1234",
        )
        student = StudentService.create_student(db_session, data)
        assert student.pin != "1234"
        assert verify_password("1234", student.pin)

    def test_create_student_invalid_belt(self, db_session):
        """Should raise 400 when belt_id doesn't exist."""
        data = StudentCreate(
            full_name="Bad Belt Student",
            category="adult",
            current_belt_id="nonexistent-belt",
            pin="1234",
        )
        with pytest.raises(HTTPException) as exc_info:
            StudentService.create_student(db_session, data)
        assert exc_info.value.status_code == 400

    def test_create_student_duplicate_registration(self, db_session):
        """Should raise 409 when registration number already in use."""
        belt = make_belt(db_session)
        make_student(db_session, registration_number="DUP001", current_belt_id=belt.id)
        db_session.commit()

        data = StudentCreate(
            full_name="Dup Student",
            category="adult",
            current_belt_id=belt.id,
            pin="1234",
            registration_number="DUP001",
        )
        with pytest.raises(HTTPException) as exc_info:
            StudentService.create_student(db_session, data)
        assert exc_info.value.status_code == 409

    def test_create_student_creates_initial_promotion(self, db_session):
        """Should create a BeltPromotion record for initial belt."""
        belt = make_belt(db_session)
        db_session.commit()

        data = StudentCreate(
            full_name="Promoted Student",
            category="adult",
            current_belt_id=belt.id,
            pin="1234",
        )
        student = StudentService.create_student(db_session, data)

        from app.models import BeltPromotion
        promotion = db_session.query(BeltPromotion).filter(
            BeltPromotion.student_id == student.id
        ).first()
        assert promotion is not None
        assert promotion.belt_id == belt.id
        assert promotion.notes == "Initial belt assignment"


class TestStudentServiceUpdate:
    """Tests for StudentService.update_student."""

    def test_update_student_name(self, db_session):
        """Should update student's full_name."""
        belt = make_belt(db_session)
        student = make_student(db_session, full_name="Old Name", current_belt_id=belt.id)
        db_session.commit()

        update = StudentUpdate(full_name="New Name")
        updated = StudentService.update_student(db_session, student.id, update)
        assert updated.full_name == "New Name"

    def test_update_student_pin_hashes(self, db_session):
        """Should hash PIN when updating."""
        belt = make_belt(db_session)
        student = make_student(db_session, current_belt_id=belt.id)
        db_session.commit()

        update = StudentUpdate(pin="5678")
        updated = StudentService.update_student(db_session, student.id, update)
        assert verify_password("5678", updated.pin)

    def test_update_nonexistent_student(self, db_session):
        """Should raise 404 for nonexistent student."""
        update = StudentUpdate(full_name="Ghost")
        with pytest.raises(HTTPException) as exc_info:
            StudentService.update_student(db_session, "nonexistent", update)
        assert exc_info.value.status_code == 404


class TestStudentServiceDeactivate:
    """Tests for StudentService.deactivate_student."""

    def test_deactivate_student(self, db_session):
        """Should set is_active to False."""
        belt = make_belt(db_session)
        student = make_student(db_session, is_active=True, current_belt_id=belt.id)
        db_session.commit()

        deactivated = StudentService.deactivate_student(db_session, student.id)
        assert deactivated.is_active is False


class TestStudentServiceProgress:
    """Tests for StudentService.get_student_progress."""

    def test_progress_with_next_belt(self, db_session):
        """Should calculate progress towards next belt."""
        belt1 = make_belt(db_session, name="White", sort_order=1)
        belt2 = make_belt(db_session, name="Blue", sort_order=2)
        et = make_event_type(db_session, name="Regular Class")
        db_session.commit()

        # Add requirement for Blue belt
        make_belt_requirement(db_session, belt_id=belt2.id, event_type_id=et.id, required_count=10)
        db_session.commit()

        student = make_student(db_session, current_belt_id=belt1.id, registration_number="P001")
        db_session.commit()

        progress = StudentService.get_student_progress(db_session, student.id)
        assert progress["current_belt"] == "White"
        assert progress["next_belt"] == "Blue"
        assert len(progress["requirements"]) == 1
        assert progress["requirements"][0]["required"] == 10
        assert progress["requirements"][0]["completed"] == 0

    def test_progress_highest_belt(self, db_session):
        """Should show message when at highest belt."""
        belt = make_belt(db_session, name="Black", sort_order=99)
        db_session.commit()

        student = make_student(db_session, current_belt_id=belt.id, registration_number="P002")
        db_session.commit()

        progress = StudentService.get_student_progress(db_session, student.id)
        assert progress["next_belt"] is None
        assert "mais alta" in progress["message"]

    def test_progress_nonexistent_student(self, db_session):
        """Should raise 404 for nonexistent student."""
        with pytest.raises(HTTPException) as exc_info:
            StudentService.get_student_progress(db_session, "nonexistent")
        assert exc_info.value.status_code == 404


class TestStudentServiceExamHistory:
    """Tests for StudentService.get_student_exam_history."""

    def test_exam_history_empty(self, db_session):
        """Should return empty list for student with no exams."""
        belt = make_belt(db_session)
        student = make_student(db_session, current_belt_id=belt.id)
        db_session.commit()

        history = StudentService.get_student_exam_history(db_session, student.id)
        assert history == []

    def test_exam_history_with_participation(self, db_session):
        """Should return exam history with participation details."""
        from app.models import ExamParticipant
        belt = make_belt(db_session, name="Blue", sort_order=2)
        et = make_event_type(db_session)
        user = make_user(db_session)
        event = make_event(db_session, event_type_id=et.id, created_by=user.id)
        exam = make_exam(db_session, event_id=event.id, belt_id=belt.id, created_by=user.id)
        student = make_student(db_session, current_belt_id=belt.id)
        db_session.commit()

        participant = ExamParticipant(
            exam_id=exam.id,
            student_id=student.id,
            role="candidate",
            status="approved",
            is_eligible=True,
        )
        db_session.add(participant)
        db_session.commit()

        history = StudentService.get_student_exam_history(db_session, student.id)
        assert len(history) == 1
        assert history[0]["exam_id"] == exam.id
        assert history[0]["role"] == "candidate"
        assert history[0]["status"] == "approved"
        assert history[0]["belt_name"] == "Blue"

    def test_exam_history_nonexistent_student(self, db_session):
        """Should raise 404 for nonexistent student."""
        with pytest.raises(HTTPException) as exc_info:
            StudentService.get_student_exam_history(db_session, "nonexistent")
        assert exc_info.value.status_code == 404


class TestStudentServiceRegistrationNumber:
    """Tests for registration number generation."""

    def test_generate_registration_number(self, db_session):
        """Should generate registration number in format seq+year+dojo_code."""
        org = make_organization(db_session)
        dojo = make_dojo(db_session, organization_id=org.id, code=5)
        db_session.commit()

        reg_num = StudentService._generate_registration_number(db_session, dojo.id)
        # Should be seq + year_suffix + dojo_code
        assert len(reg_num) > 0
        assert str(dojo.code) in reg_num

    def test_generate_registration_number_no_dojo(self, db_session):
        """Should use default dojo code 1 when no dojo_id."""
        reg_num = StudentService._generate_registration_number(db_session, None)
        assert len(reg_num) > 0