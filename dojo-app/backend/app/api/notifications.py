"""Public endpoints for the Notification Hub: opt-in, subscription, and history."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limiter import RateLimiter
from app.schemas import NotificationResponse, PushSubscribeRequest, StudentCredentials, VapidPublicKeyResponse
from app.services import NotificationService

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])
notification_rate_limiter = RateLimiter()
INVALID_CREDENTIALS = "Matrícula ou PIN inválidos."


def _rate_limit(request: Request, registration_number: str) -> None:
    client_ip = request.client.host if request.client else "unknown"
    notification_rate_limiter.check_rate_limit(f"ip:{client_ip}")
    notification_rate_limiter.check_rate_limit(f"registration:{registration_number}")


def _authenticate_or_401(db: Session, data: StudentCredentials, request: Request):
    _rate_limit(request, data.registration_number)
    student = NotificationService.authenticate_student(db, data.registration_number, data.pin)
    if not student:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)
    return student


@router.get("/vapid-public-key", response_model=VapidPublicKeyResponse)
def get_vapid_public_key():
    """Public by design -- a VAPID public key is meant to be exposed to the browser."""
    return VapidPublicKeyResponse(public_key=get_settings().vapid_public_key)


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
def subscribe(data: PushSubscribeRequest, request: Request, db: Session = Depends(get_db)):
    """Link a browser push subscription to a student (NH-01/NH-02)."""
    student = _authenticate_or_401(db, data, request)
    NotificationService.add_subscription(db, student.id, data.endpoint, data.keys.p256dh, data.keys.auth)
    return {"status": "subscribed"}


@router.post("/history", response_model=list[NotificationResponse])
def get_history(data: StudentCredentials, request: Request, db: Session = Depends(get_db)):
    """Return a student's full notification history (NH-08)."""
    student = _authenticate_or_401(db, data, request)
    return NotificationService.get_history(db, student.id)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: str, data: StudentCredentials, request: Request, db: Session = Depends(get_db)
):
    """Mark one notification read, persisted across sessions/devices (NH-08)."""
    student = _authenticate_or_401(db, data, request)
    notification = NotificationService.mark_read(db, notification_id, student.id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification
