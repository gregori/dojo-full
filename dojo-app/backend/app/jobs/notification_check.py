"""Standalone entrypoint for the notification-trigger check.

Invoked by a Kubernetes CronJob (dojo-infra/k8s/backend/notification-check-cronjob.yaml,
the confirmed-live manifest set -- see plan.md Autocritica), not by the FastAPI
app -- this codebase has no in-process scheduler and none is introduced for
this feature.
"""

import logging

from app.core.database import SessionLocal
from app.services.notification_trigger_service import NotificationTriggerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    db = SessionLocal()
    try:
        pre_checkin_count = NotificationTriggerService.check_pre_checkin_reminders(db)
        medical_exam_count = NotificationTriggerService.check_medical_exam_reminders(db)
        mensalidade_count = NotificationTriggerService.check_mensalidade_reminders(db)
        logger.info(
            "Notification check complete: pre_checkin=%d medical_exam=%d mensalidade=%d",
            pre_checkin_count,
            medical_exam_count,
            mensalidade_count,
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
