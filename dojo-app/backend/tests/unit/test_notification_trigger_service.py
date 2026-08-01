"""Unit tests for NotificationTriggerService: NH-03/04/05/06/07 trigger detection."""

from datetime import date, datetime, time, timedelta

import pytest
from freezegun import freeze_time
from sqlalchemy.orm import sessionmaker

from app.core.timezone import APP_TIMEZONE, local_today
from app.models import Notification
from app.services import NotificationService
from app.services.notification_trigger_service import (
    MEDICAL_EXAM_LEAD,
    MENSALIDADE_LEAD,
    PRE_CHECKIN_LEAD,
    NotificationTriggerService,
)
from tests.unit.conftest import (
    make_belt,
    make_event,
    make_medical_exam,
    make_mensalidade,
    make_payment,
    make_pre_checkin,
    make_student,
)

# Noon UTC on this date is 09:00 in America/Sao_Paulo (UTC-3) -- same calendar
# day, so this instant is safe to use for tests that don't specifically probe
# the UTC/local calendar-day boundary.
FROZEN_INSTANT = "2026-06-15 12:00:00"


def _local(target_date: date, hour: int = 10) -> datetime:
    """A tz-aware datetime for a given calendar day in the app's timezone."""
    return datetime.combine(target_date, time(hour, 0), tzinfo=APP_TIMEZONE)


class TestPreCheckInReminders:
    """NH-03."""

    def test_fires_for_eligible_student_with_no_pre_checkin(self, db_session):
        with freeze_time(FROZEN_INSTANT):
            student = make_student(db_session)
            event = make_event(db_session, start_datetime=_local(local_today() + PRE_CHECKIN_LEAD))
            db_session.commit()

            fired = NotificationTriggerService.check_pre_checkin_reminders(db_session)

        assert fired == 1
        notification = db_session.query(Notification).filter(Notification.student_id == student.id).first()
        assert notification is not None
        assert notification.notification_type == "pre_checkin_reminder"
        assert notification.reference_id == event.id
        assert event.title in notification.message

    def test_does_not_fire_for_belt_ineligible_student(self, db_session):
        with freeze_time(FROZEN_INSTANT):
            low_belt = make_belt(db_session, sort_order=1)
            high_belt = make_belt(db_session, sort_order=10)
            make_student(db_session, current_belt_id=low_belt.id)
            make_event(
                db_session,
                start_datetime=_local(local_today() + PRE_CHECKIN_LEAD),
                minimum_belt_id=high_belt.id,
            )
            db_session.commit()

            fired = NotificationTriggerService.check_pre_checkin_reminders(db_session)

        assert fired == 0
        assert db_session.query(Notification).count() == 0

    @pytest.mark.parametrize("status", ["confirmed", "converted"])
    def test_does_not_fire_when_already_checked_in(self, db_session, status):
        with freeze_time(FROZEN_INSTANT):
            student = make_student(db_session)
            event = make_event(db_session, start_datetime=_local(local_today() + PRE_CHECKIN_LEAD))
            make_pre_checkin(db_session, event_id=event.id, student_id=student.id, status=status)
            db_session.commit()

            fired = NotificationTriggerService.check_pre_checkin_reminders(db_session)

        assert fired == 0

    def test_does_not_fire_for_cancelled_event(self, db_session):
        with freeze_time(FROZEN_INSTANT):
            make_student(db_session)
            make_event(db_session, start_datetime=_local(local_today() + PRE_CHECKIN_LEAD), status="cancelled")
            db_session.commit()

            fired = NotificationTriggerService.check_pre_checkin_reminders(db_session)

        assert fired == 0

    def test_fires_when_only_pre_checkin_is_cancelled(self, db_session):
        with freeze_time(FROZEN_INSTANT):
            student = make_student(db_session)
            event = make_event(db_session, start_datetime=_local(local_today() + PRE_CHECKIN_LEAD))
            make_pre_checkin(db_session, event_id=event.id, student_id=student.id, status="cancelled")
            db_session.commit()

            fired = NotificationTriggerService.check_pre_checkin_reminders(db_session)

        assert fired == 1


class TestMedicalExamReminders:
    """NH-04."""

    def test_fires_for_active_exam_expiring_at_lead_time(self, db_session):
        with freeze_time(FROZEN_INSTANT):
            student = make_student(db_session)
            exam = make_medical_exam(
                db_session, student_id=student.id, expires_at=_local(local_today() + MEDICAL_EXAM_LEAD)
            )
            db_session.commit()

            fired = NotificationTriggerService.check_medical_exam_reminders(db_session)

        assert fired == 1
        notification = db_session.query(Notification).filter(Notification.student_id == student.id).first()
        assert notification.notification_type == "medical_exam_expiring"
        assert notification.reference_id == exam.id

    def test_does_not_fire_for_superseded_exam(self, db_session):
        with freeze_time(FROZEN_INSTANT):
            student = make_student(db_session)
            make_medical_exam(
                db_session,
                student_id=student.id,
                status="superseded",
                expires_at=_local(local_today() + MEDICAL_EXAM_LEAD),
            )
            db_session.commit()

            fired = NotificationTriggerService.check_medical_exam_reminders(db_session)

        assert fired == 0

    def test_does_not_fire_for_student_with_no_exam(self, db_session):
        with freeze_time(FROZEN_INSTANT):
            make_student(db_session)
            db_session.commit()

            fired = NotificationTriggerService.check_medical_exam_reminders(db_session)

        assert fired == 0


class TestMensalidadeReminders:
    """NH-05."""

    def test_fires_for_due_mensalidade_even_if_partially_paid(self, db_session):
        with freeze_time(FROZEN_INSTANT):
            student = make_student(db_session)
            mensalidade = make_mensalidade(
                db_session,
                student_id=student.id,
                due_date=_local(local_today() + MENSALIDADE_LEAD),
            )
            make_payment(db_session, student_id=student.id, amount=mensalidade.amount / 2)
            db_session.commit()

            fired = NotificationTriggerService.check_mensalidade_reminders(db_session)

        assert fired == 1
        notification = db_session.query(Notification).filter(Notification.student_id == student.id).first()
        assert notification.notification_type == "mensalidade_due"
        assert notification.reference_id == mensalidade.id

    def test_does_not_fire_once_fully_paid(self, db_session):
        with freeze_time(FROZEN_INSTANT):
            student = make_student(db_session)
            mensalidade = make_mensalidade(
                db_session,
                student_id=student.id,
                due_date=_local(local_today() + MENSALIDADE_LEAD),
            )
            make_payment(db_session, student_id=student.id, amount=mensalidade.amount)
            db_session.commit()

            fired = NotificationTriggerService.check_mensalidade_reminders(db_session)

        assert fired == 0


class TestIdempotencyAndConcurrency:
    """NH-06."""

    def test_calling_the_same_routine_twice_does_not_duplicate(self, db_session):
        with freeze_time(FROZEN_INSTANT):
            make_student(db_session)
            make_event(db_session, start_datetime=_local(local_today() + PRE_CHECKIN_LEAD))
            db_session.commit()

            first_fired = NotificationTriggerService.check_pre_checkin_reminders(db_session)
            second_fired = NotificationTriggerService.check_pre_checkin_reminders(db_session)

        assert first_fired == 1
        assert second_fired == 0
        assert db_session.query(Notification).count() == 1

    def test_create_if_new_survives_simulated_concurrent_race(self, db_session, db_engine):
        student = make_student(db_session)
        db_session.commit()

        competitor_session = sessionmaker(bind=db_engine)()
        competitor = Notification(
            student_id=student.id,
            notification_type="pre_checkin_reminder",
            reference_id="event-race",
            message="Competitor message",
        )

        original_commit = db_session.commit

        def racing_commit():
            # Simulate a concurrent writer winning the race between our own
            # existing-row check and our own commit.
            competitor_session.add(competitor)
            competitor_session.commit()
            original_commit()

        db_session.commit = racing_commit
        try:
            result = NotificationService.create_if_new(
                db_session, student.id, "pre_checkin_reminder", "event-race", "Our message"
            )
        finally:
            db_session.commit = original_commit

        assert result is None
        count = (
            db_session.query(Notification)
            .filter(Notification.student_id == student.id, Notification.reference_id == "event-race")
            .count()
        )
        assert count == 1
        competitor_session.close()


class TestNoBackfill:
    """NH-07: only future crossings, from go-live onward, ever fire."""

    def test_event_past_threshold_never_fires(self, db_session):
        with freeze_time(FROZEN_INSTANT):
            make_student(db_session)
            make_event(db_session, start_datetime=_local(local_today() - timedelta(days=5)))
            db_session.commit()

            fired = NotificationTriggerService.check_pre_checkin_reminders(db_session)

        assert fired == 0
        assert db_session.query(Notification).count() == 0

    def test_medical_exam_past_threshold_never_fires(self, db_session):
        with freeze_time(FROZEN_INSTANT):
            student = make_student(db_session)
            make_medical_exam(db_session, student_id=student.id, expires_at=_local(local_today() - timedelta(days=1)))
            db_session.commit()

            fired = NotificationTriggerService.check_medical_exam_reminders(db_session)

        assert fired == 0

    def test_mensalidade_past_threshold_never_fires(self, db_session):
        with freeze_time(FROZEN_INSTANT):
            student = make_student(db_session)
            make_mensalidade(db_session, student_id=student.id, due_date=_local(local_today() - timedelta(days=1)))
            db_session.commit()

            fired = NotificationTriggerService.check_mensalidade_reminders(db_session)

        assert fired == 0


class TestPushAttemptedOnlyOnActualFire:
    """Push send is impossible on a duplicate/losing-race path (plan.md Autocritica)."""

    def test_push_called_once_and_not_again_for_duplicate(self, db_session, monkeypatch):
        calls = []
        monkeypatch.setattr(
            "app.services.notification_trigger_service.PushService.send_to_student",
            lambda db, student, title, body: calls.append(student.id),
        )
        with freeze_time(FROZEN_INSTANT):
            make_student(db_session)
            make_event(db_session, start_datetime=_local(local_today() + PRE_CHECKIN_LEAD))
            db_session.commit()

            NotificationTriggerService.check_pre_checkin_reminders(db_session)
            NotificationTriggerService.check_pre_checkin_reminders(db_session)

        assert len(calls) == 1


class TestTimezoneBoundary:
    """The target-date computation must use the Sao Paulo date, not the UTC date."""

    def test_target_date_uses_sao_paulo_date_not_utc_date(self, db_session):
        # 01:00 UTC on the 16th is still 22:00 on the 15th in America/Sao_Paulo (UTC-3).
        with freeze_time("2026-06-16 01:00:00"):
            sao_paulo_today = date(2026, 6, 15)
            assert local_today() == sao_paulo_today

            make_student(db_session)
            make_event(db_session, start_datetime=_local(sao_paulo_today + PRE_CHECKIN_LEAD))
            db_session.commit()

            fired = NotificationTriggerService.check_pre_checkin_reminders(db_session)

        assert fired == 1
