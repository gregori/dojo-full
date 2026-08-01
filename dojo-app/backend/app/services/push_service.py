"""Best-effort Web Push delivery via VAPID (RFC 8292), using pywebpush."""

import json
import logging

from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import PushSubscription, Student

logger = logging.getLogger(__name__)


class PushService:
    @staticmethod
    def send_to_student(db: Session, student: Student, title: str, body: str) -> None:
        """Send one push message to every active subscription for a student (NH-09).

        Best-effort: a failed/stale subscription is logged and skipped, never
        raised -- push delivery failure never blocks the in-app Notification
        row (already committed by the caller before this runs) from existing.
        Subscription-staleness cleanup is an explicit Open Question, not a v1
        requirement (requirements.md), and is deliberately not implemented here.
        """
        settings = get_settings()
        subscriptions = db.query(PushSubscription).filter(PushSubscription.student_id == student.id).all()
        payload = json.dumps({"title": title, "body": body})
        for subscription in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": subscription.endpoint,
                        "keys": {"p256dh": subscription.p256dh_key, "auth": subscription.auth_key},
                    },
                    data=payload,
                    vapid_private_key=settings.vapid_private_key,
                    vapid_claims={"sub": settings.vapid_subject},
                )
            except WebPushException:
                logger.warning("Push delivery failed for subscription %s", subscription.id, exc_info=True)
