"""Unit tests for app.services.event_service module."""

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app.schemas import EventCreate, EventTypeCreate, EventTypeUpdate, EventUpdate
from app.services.event_service import EventService, EventTypeService
from tests.unit.conftest import (
    make_event,
    make_event_type,
    make_user,
)


class TestEventTypeServiceGet:
    """Tests for EventTypeService get operations."""

    def test_get_event_type_by_id(self, db_session):
        """Should return event type by ID."""
        et = make_event_type(db_session, name="Regular Class")
        db_session.commit()

        found = EventTypeService.get_event_type(db_session, et.id)
        assert found is not None
        assert found.name == "Regular Class"

    def test_get_event_type_not_found(self, db_session):
        """Should return None for nonexistent ID."""
        found = EventTypeService.get_event_type(db_session, "nonexistent")
        assert found is None

    def test_get_event_types_list(self, db_session):
        """Should return list of event types."""
        make_event_type(db_session, name="Type A")
        make_event_type(db_session, name="Type B")
        db_session.commit()

        types = EventTypeService.get_event_types(db_session)
        assert len(types) >= 2


class TestEventTypeServiceCreate:
    """Tests for EventTypeService.create_event_type."""

    def test_create_event_type(self, db_session):
        """Should create a new event type."""
        data = EventTypeCreate(name="Seminar", color="#ff0000", counts_for_belt=True)
        et = EventTypeService.create_event_type(db_session, data)
        assert et.id is not None
        assert et.name == "Seminar"
        assert et.color == "#ff0000"
        assert et.counts_for_belt is True


class TestEventTypeServiceUpdate:
    """Tests for EventTypeService.update_event_type."""

    def test_update_event_type_name(self, db_session):
        """Should update event type name."""
        et = make_event_type(db_session, name="Old Name")
        db_session.commit()

        update = EventTypeUpdate(name="New Name")
        updated = EventTypeService.update_event_type(db_session, et.id, update)
        assert updated.name == "New Name"

    def test_update_nonexistent_event_type(self, db_session):
        """Should raise 404 for nonexistent event type."""
        update = EventTypeUpdate(name="Ghost")
        with pytest.raises(HTTPException) as exc_info:
            EventTypeService.update_event_type(db_session, "nonexistent", update)
        assert exc_info.value.status_code == 404


class TestEventTypeServiceDelete:
    """Tests for EventTypeService.delete_event_type."""

    def test_delete_event_type(self, db_session):
        """Should delete event type."""
        et = make_event_type(db_session, name="To Delete")
        db_session.commit()
        et_id = et.id

        EventTypeService.delete_event_type(db_session, et_id)
        assert EventTypeService.get_event_type(db_session, et_id) is None

    def test_delete_nonexistent_event_type(self, db_session):
        """Should raise 404 for nonexistent event type."""
        with pytest.raises(HTTPException) as exc_info:
            EventTypeService.delete_event_type(db_session, "nonexistent")
        assert exc_info.value.status_code == 404


class TestEventServiceGet:
    """Tests for EventService get operations."""

    def test_get_event_by_id(self, db_session):
        """Should return event by ID."""
        event = make_event(db_session, title="Test Event")
        db_session.commit()

        found = EventService.get_event(db_session, event.id)
        assert found is not None
        assert found.title == "Test Event"

    def test_get_event_not_found(self, db_session):
        """Should return None for nonexistent ID."""
        found = EventService.get_event(db_session, "nonexistent")
        assert found is None

    def test_get_event_by_token(self, db_session):
        """Should return event by check_in_token."""
        event = make_event(db_session, title="Token Event")
        db_session.commit()

        found = EventService.get_event_by_token(db_session, event.check_in_token)
        assert found is not None
        assert found.id == event.id

    def test_get_events_with_status_filter(self, db_session):
        """Should filter events by status."""
        make_event(db_session, title="Scheduled Event", status="scheduled")
        make_event(db_session, title="Cancelled Event", status="cancelled")
        db_session.commit()

        scheduled = EventService.get_events(db_session, status="scheduled")
        assert all(e.status == "scheduled" for e in scheduled)

    def test_get_events_with_type_filter(self, db_session):
        """Should filter events by event_type_id."""
        et1 = make_event_type(db_session, name="Type A")
        et2 = make_event_type(db_session, name="Type B")
        user = make_user(db_session)
        db_session.commit()

        make_event(db_session, event_type_id=et1.id, created_by=user.id, title="Event A")
        make_event(db_session, event_type_id=et2.id, created_by=user.id, title="Event B")
        db_session.commit()

        filtered = EventService.get_events(db_session, event_type_id=et1.id)
        assert all(e.event_type_id == et1.id for e in filtered)


class TestEventServiceCreate:
    """Tests for EventService.create_event."""

    def test_create_event(self, db_session):
        """Should create a new event with scheduled status."""
        et = make_event_type(db_session)
        user = make_user(db_session)
        db_session.commit()

        data = EventCreate(
            title="New Event",
            event_type_id=et.id,
            start_datetime=datetime.now(UTC),
        )
        event = EventService.create_event(db_session, data, created_by=user.id)
        assert event.id is not None
        assert event.title == "New Event"
        assert event.status == "scheduled"
        assert event.created_by == user.id


class TestEventServiceUpdate:
    """Tests for EventService.update_event."""

    def test_update_event_title(self, db_session):
        """Should update event title."""
        event = make_event(db_session, title="Old Title")
        db_session.commit()

        update = EventUpdate(title="New Title")
        updated = EventService.update_event(db_session, event.id, update)
        assert updated.title == "New Title"

    def test_update_nonexistent_event(self, db_session):
        """Should raise 404 for nonexistent event."""
        update = EventUpdate(title="Ghost")
        with pytest.raises(HTTPException) as exc_info:
            EventService.update_event(db_session, "nonexistent", update)
        assert exc_info.value.status_code == 404


class TestEventServiceDelete:
    """Tests for EventService.delete_event (soft delete)."""

    def test_delete_event_sets_cancelled(self, db_session):
        """Should set status to 'cancelled' instead of hard delete."""
        event = make_event(db_session, title="To Cancel")
        db_session.commit()

        EventService.delete_event(db_session, event.id)
        db_session.commit()

        # Refresh
        db_session.expire(event)
        assert event.status == "cancelled"

    def test_delete_nonexistent_event(self, db_session):
        """Should raise 404 for nonexistent event."""
        with pytest.raises(HTTPException) as exc_info:
            EventService.delete_event(db_session, "nonexistent")
        assert exc_info.value.status_code == 404
