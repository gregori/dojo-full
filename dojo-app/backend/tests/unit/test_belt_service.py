"""Unit tests for app.services.belt_service module."""

import pytest
from fastapi import HTTPException

from app.schemas import BeltCreate, BeltRequirementCreate, BeltRequirementUpdate, BeltUpdate
from app.services.belt_service import BeltService
from tests.unit.conftest import (
    make_belt,
    make_belt_promotion,
    make_belt_requirement,
    make_event_type,
    make_exam,
    make_student,
)


class TestBeltServiceGet:
    """Tests for BeltService get operations."""

    def test_get_belt_by_id(self, db_session):
        """Should return belt by ID."""
        belt = make_belt(db_session, name="White")
        db_session.commit()

        found = BeltService.get_belt(db_session, belt.id)
        assert found is not None
        assert found.name == "White"

    def test_get_belt_not_found(self, db_session):
        """Should return None for nonexistent ID."""
        found = BeltService.get_belt(db_session, "nonexistent")
        assert found is None

    def test_get_belts_all(self, db_session):
        """Should return all belts ordered by sort_order."""
        make_belt(db_session, name="White", sort_order=1)
        make_belt(db_session, name="Blue", sort_order=2)
        db_session.commit()

        belts = BeltService.get_belts(db_session)
        assert len(belts) >= 2
        # Should be ordered by sort_order
        assert belts[0].sort_order <= belts[1].sort_order

    def test_get_belts_by_category(self, db_session):
        """Should filter belts by category."""
        make_belt(db_session, name="Adult White", category="adult", sort_order=1)
        make_belt(db_session, name="Child White", category="child", sort_order=1)
        db_session.commit()

        adults = BeltService.get_belts(db_session, category="adult")
        assert all(b.category == "adult" for b in adults)


class TestBeltServiceCreate:
    """Tests for BeltService.create_belt."""

    def test_create_belt(self, db_session):
        """Should create a new belt."""
        data = BeltCreate(name="Yellow", category="adult", sort_order=3)
        belt = BeltService.create_belt(db_session, data)
        assert belt.id is not None
        assert belt.name == "Yellow"
        assert belt.category == "adult"
        assert belt.sort_order == 3


class TestBeltServiceUpdate:
    """Tests for BeltService.update_belt."""

    def test_update_belt_name(self, db_session):
        """Should update belt name."""
        belt = make_belt(db_session, name="Old Name")
        db_session.commit()

        update = BeltUpdate(name="New Name")
        updated = BeltService.update_belt(db_session, belt.id, update)
        assert updated.name == "New Name"

    def test_update_nonexistent_belt(self, db_session):
        """Should raise 404 for nonexistent belt."""
        update = BeltUpdate(name="Ghost")
        with pytest.raises(HTTPException) as exc_info:
            BeltService.update_belt(db_session, "nonexistent", update)
        assert exc_info.value.status_code == 404


class TestBeltServiceDelete:
    """Tests for BeltService.delete_belt."""

    def test_delete_belt(self, db_session):
        """Should delete belt."""
        belt = make_belt(db_session, name="To Delete")
        db_session.commit()
        belt_id = belt.id

        BeltService.delete_belt(db_session, belt_id)
        assert BeltService.get_belt(db_session, belt_id) is None

    def test_delete_nonexistent_belt(self, db_session):
        """Should raise 404 for nonexistent belt."""
        with pytest.raises(HTTPException) as exc_info:
            BeltService.delete_belt(db_session, "nonexistent")
        assert exc_info.value.status_code == 404

    def test_delete_belt_assigned_to_student_raises_409(self, db_session):
        """Should raise 409 instead of crashing when a student is assigned to the belt.

        Regression test: deleting a belt that students are currently assigned to
        used to raise an unhandled IntegrityError (500), since SQLAlchemy's default
        ORM behavior nulls out Student.current_belt_id before the delete, and that
        column is NOT NULL.
        """
        belt = make_belt(db_session, name="In Use")
        make_student(db_session, current_belt_id=belt.id)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            BeltService.delete_belt(db_session, belt.id)
        assert exc_info.value.status_code == 409
        assert BeltService.get_belt(db_session, belt.id) is not None

    def test_delete_belt_with_promotion_history_raises_409(self, db_session):
        """Should raise 409 when the belt has promotion history."""
        belt = make_belt(db_session, name="Promoted To")
        other_belt = make_belt(db_session, name="Other")
        student = make_student(db_session, current_belt_id=other_belt.id)
        make_belt_promotion(db_session, student_id=student.id, belt_id=belt.id)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            BeltService.delete_belt(db_session, belt.id)
        assert exc_info.value.status_code == 409
        assert BeltService.get_belt(db_session, belt.id) is not None

    def test_delete_belt_with_exam_raises_409(self, db_session):
        """Should raise 409 when the belt has an exam associated with it."""
        belt = make_belt(db_session, name="Exam Belt")
        make_exam(db_session, belt_id=belt.id)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            BeltService.delete_belt(db_session, belt.id)
        assert exc_info.value.status_code == 409
        assert BeltService.get_belt(db_session, belt.id) is not None

    def test_delete_belt_with_requirement_raises_409(self, db_session):
        """Should raise 409 when the belt has a requirement defined."""
        belt = make_belt(db_session, name="Requirement Belt")
        et = make_event_type(db_session)
        make_belt_requirement(db_session, belt_id=belt.id, event_type_id=et.id)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            BeltService.delete_belt(db_session, belt.id)
        assert exc_info.value.status_code == 409
        assert BeltService.get_belt(db_session, belt.id) is not None


class TestBeltRequirementService:
    """Tests for BeltService requirement operations."""

    def test_create_requirement(self, db_session):
        """Should create a belt requirement."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        db_session.commit()

        data = BeltRequirementCreate(
            belt_id=belt.id,
            event_type_id=et.id,
            required_count=20,
            description="Regular classes",
        )
        req = BeltService.create_requirement(db_session, data)
        assert req.id is not None
        assert req.belt_id == belt.id
        assert req.required_count == 20

    def test_get_requirements_by_belt(self, db_session):
        """Should return requirements for a belt."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        db_session.commit()

        make_belt_requirement(db_session, belt_id=belt.id, event_type_id=et.id)
        db_session.commit()

        reqs = BeltService.get_requirements_by_belt(db_session, belt.id)
        assert len(reqs) >= 1

    def test_update_requirement(self, db_session):
        """Should update a requirement."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        req = make_belt_requirement(db_session, belt_id=belt.id, event_type_id=et.id, required_count=10)
        db_session.commit()

        update = BeltRequirementUpdate(required_count=15)
        updated = BeltService.update_requirement(db_session, req.id, update)
        assert updated.required_count == 15

    def test_update_nonexistent_requirement(self, db_session):
        """Should raise 404 for nonexistent requirement."""
        update = BeltRequirementUpdate(required_count=15)
        with pytest.raises(HTTPException) as exc_info:
            BeltService.update_requirement(db_session, "nonexistent", update)
        assert exc_info.value.status_code == 404

    def test_delete_requirement(self, db_session):
        """Should delete a requirement."""
        belt = make_belt(db_session)
        et = make_event_type(db_session)
        req = make_belt_requirement(db_session, belt_id=belt.id, event_type_id=et.id)
        db_session.commit()
        req_id = req.id

        BeltService.delete_requirement(db_session, req_id)
        # Verify it's gone
        from app.models import BeltRequirement

        assert db_session.query(BeltRequirement).filter(BeltRequirement.id == req_id).first() is None

    def test_delete_nonexistent_requirement(self, db_session):
        """Should raise 404 for nonexistent requirement."""
        with pytest.raises(HTTPException) as exc_info:
            BeltService.delete_requirement(db_session, "nonexistent")
        assert exc_info.value.status_code == 404
