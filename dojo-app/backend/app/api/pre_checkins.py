"""Public and instructor-only endpoints for pre-check-ins."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limiter import precheckin_rate_limiter
from app.dependencies.auth import get_current_instructor_or_admin
from app.schemas import (
    PreCheckInCount,
    PreCheckInPublicResponse,
    PreCheckInRequest,
    PreCheckInRosterItem,
    PublicPreCheckInEvent,
)
from app.services import PreCheckInService

router = APIRouter(prefix="/api/v1/pre-checkins", tags=["pre-check-ins"])
GENERIC_MESSAGE = "If the supplied details are valid, your request has been processed."


def _rate_limit(request: Request, registration_number: str) -> None:
    client_ip = request.client.host if request.client else "unknown"
    precheckin_rate_limiter.check_rate_limit(f"ip:{client_ip}")
    precheckin_rate_limiter.check_rate_limit(f"registration:{registration_number}")


@router.get("/events", response_model=list[PublicPreCheckInEvent])
def list_public_pre_checkin_events(db: Session = Depends(get_db)):
    """List event choices that are scheduled and still open for public pre-check-in."""
    return PreCheckInService.get_public_events(db)


@router.post("/confirm", response_model=PreCheckInPublicResponse)
def confirm_pre_checkin(data: PreCheckInRequest, request: Request, db: Session = Depends(get_db)):
    """Confirm an upcoming event without exposing student details on failed authentication."""
    _rate_limit(request, data.registration_number)
    student = PreCheckInService.authenticate_student(db, data.registration_number, data.pin)
    if not student:
        return PreCheckInPublicResponse(status="accepted", message=GENERIC_MESSAGE)
    PreCheckInService.confirm(db, data.event_id, student)
    return PreCheckInPublicResponse(status="accepted", message=GENERIC_MESSAGE)


@router.post("/cancel", response_model=PreCheckInPublicResponse)
def cancel_pre_checkin(data: PreCheckInRequest, request: Request, db: Session = Depends(get_db)):
    """Cancel a confirmation without exposing whether one existed."""
    _rate_limit(request, data.registration_number)
    student = PreCheckInService.authenticate_student(db, data.registration_number, data.pin)
    if not student:
        return PreCheckInPublicResponse(status="accepted", message=GENERIC_MESSAGE)
    PreCheckInService.cancel(db, data.event_id, student)
    return PreCheckInPublicResponse(status="accepted", message=GENERIC_MESSAGE)


@router.get("/events/{event_id}", response_model=list[PreCheckInRosterItem])
def list_confirmed_pre_checkins(
    event_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """List confirmed students for an event (instructor/admin only)."""
    return PreCheckInService.get_confirmed_roster(db, event_id)


@router.get("/events/{event_id}/count", response_model=PreCheckInCount)
def get_pre_checkin_count(
    event_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """Return the number of current confirmations (instructor/admin only)."""
    return PreCheckInCount(event_id=event_id, confirmed_count=PreCheckInService.confirmed_count(db, event_id))
