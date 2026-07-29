from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_instructor_or_admin
from app.schemas import (
    EventSeriesCreate,
    EventSeriesResponse,
    EventSeriesUpdate,
    GenerateOccurrencesResponse,
)
from app.services import EventSeriesService

router = APIRouter(prefix="/api/v1/event-series", tags=["event-series"])


@router.get("", response_model=list[EventSeriesResponse])
def list_series(
    is_active: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """List all event series."""
    return EventSeriesService.get_all_series(db, is_active=is_active, skip=skip, limit=limit)


@router.get("/{series_id}", response_model=EventSeriesResponse)
def get_series(series_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)):
    """Get event series by ID."""
    return EventSeriesService.get_series(db, series_id)


@router.post("", response_model=EventSeriesResponse, status_code=status.HTTP_201_CREATED)
def create_series(
    data: EventSeriesCreate, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """Create a new event series."""
    return EventSeriesService.create_series(db, data, current_user.id)


@router.put("/{series_id}", response_model=EventSeriesResponse)
def update_series(
    series_id: str,
    data: EventSeriesUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """Update event series, propagating to not-yet-occurred generated occurrences."""
    return EventSeriesService.update_series(db, series_id, data)


@router.delete("/{series_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_series(
    series_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """End a series: deactivates it, auto-cancelling not-yet-occurred occurrences."""
    EventSeriesService.deactivate_series(db, series_id)


@router.post("/{series_id}/generate", response_model=GenerateOccurrencesResponse)
def generate_occurrences(
    series_id: str,
    window_days: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """Generate Event occurrences for a series within a rolling window."""
    from app.services.event_series_service import DEFAULT_GENERATION_WINDOW_DAYS

    return EventSeriesService.generate_occurrences(
        db, series_id, window_days=window_days if window_days is not None else DEFAULT_GENERATION_WINDOW_DAYS
    )


@router.get("/{series_id}/qr-code")
def get_series_qr_code(
    series_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """Get QR code token for series check-in."""
    series = EventSeriesService.get_series(db, series_id)
    return {"check_in_token": series.check_in_token, "url": f"/checkin?token={series.check_in_token}"}
