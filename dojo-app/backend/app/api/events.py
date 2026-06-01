from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas import (
    EventCreate, EventUpdate, EventResponse, EventWithDetails,
    EventTypeCreate, EventTypeUpdate, EventTypeResponse
)
from app.services import EventService, EventTypeService
from app.dependencies.auth import get_current_user, get_current_admin, get_current_instructor_or_admin

router = APIRouter(prefix="/api/v1/events", tags=["events"])


# Event Types
@router.get("/types", response_model=List[EventTypeResponse])
def list_event_types(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_instructor_or_admin)
):
    """List all event types."""
    return EventTypeService.get_event_types(db, skip=skip, limit=limit)


@router.post("/types", response_model=EventTypeResponse, status_code=status.HTTP_201_CREATED)
def create_event_type(
    event_type_data: EventTypeCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Create a new event type (admin only)."""
    return EventTypeService.create_event_type(db, event_type_data)


@router.put("/types/{event_type_id}", response_model=EventTypeResponse)
def update_event_type(
    event_type_id: str,
    event_type_data: EventTypeUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Update event type (admin only)."""
    return EventTypeService.update_event_type(db, event_type_id, event_type_data)


@router.delete("/types/{event_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_type(
    event_type_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Delete event type (admin only)."""
    EventTypeService.delete_event_type(db, event_type_id)


# Events
@router.get("", response_model=List[EventResponse])
def list_events(
    status: Optional[str] = None,
    event_type_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_instructor_or_admin)
):
    """List all events."""
    return EventService.get_events(db, status=status, event_type_id=event_type_id, skip=skip, limit=limit)


@router.get("/{event_id}", response_model=EventWithDetails)
def get_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_instructor_or_admin)
):
    """Get event by ID."""
    return EventService.get_event(db, event_id)


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_instructor_or_admin)
):
    """Create a new event."""
    return EventService.create_event(db, event_data, current_user.id)


@router.put("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: str,
    event_data: EventUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_instructor_or_admin)
):
    """Update event."""
    return EventService.update_event(db, event_id, event_data)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_instructor_or_admin)
):
    """Cancel event."""
    EventService.delete_event(db, event_id)


@router.get("/{event_id}/qr-code")
def get_event_qr_code(
    event_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_instructor_or_admin)
):
    """Get QR code token for event check-in."""
    event = EventService.get_event(db, event_id)
    return {"check_in_token": event.check_in_token, "url": f"/checkin?token={event.check_in_token}"}
