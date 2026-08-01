"""Unit tests for NotificationService: authentication, idempotency, history, and read state."""

from app.core.security import get_password_hash
from app.services import NotificationService
from tests.unit.conftest import make_notification, make_student


class TestAuthenticateStudent:
    def test_valid_credentials_return_student(self, db_session):
        student = make_student(db_session, registration_number="REG-AUTH", pin=get_password_hash("1234"))
        db_session.commit()

        result = NotificationService.authenticate_student(db_session, "REG-AUTH", "1234")

        assert result is not None
        assert result.id == student.id

    def test_wrong_pin_returns_none(self, db_session):
        make_student(db_session, registration_number="REG-WRONG")
        db_session.commit()

        assert NotificationService.authenticate_student(db_session, "REG-WRONG", "0000") is None

    def test_unknown_registration_returns_none(self, db_session):
        assert NotificationService.authenticate_student(db_session, "UNKNOWN", "1234") is None

    def test_inactive_student_returns_none(self, db_session):
        make_student(db_session, registration_number="REG-INACTIVE", is_active=False)
        db_session.commit()

        assert NotificationService.authenticate_student(db_session, "REG-INACTIVE", "1234") is None


class TestCreateIfNew:
    def test_first_call_creates_and_returns_row(self, db_session):
        student = make_student(db_session)
        db_session.commit()

        notification = NotificationService.create_if_new(
            db_session, student.id, "pre_checkin_reminder", "event-1", "Hello"
        )

        assert notification is not None
        assert notification.student_id == student.id

    def test_second_call_with_same_key_returns_none_and_leaves_one_row(self, db_session):
        from app.models import Notification

        student = make_student(db_session)
        db_session.commit()

        first = NotificationService.create_if_new(db_session, student.id, "pre_checkin_reminder", "event-1", "Hello")
        second = NotificationService.create_if_new(db_session, student.id, "pre_checkin_reminder", "event-1", "Hello")

        assert first is not None
        assert second is None
        count = db_session.query(Notification).filter(Notification.student_id == student.id).count()
        assert count == 1


class TestAddSubscription:
    def test_creates_a_push_subscription(self, db_session):
        student = make_student(db_session)
        db_session.commit()

        subscription = NotificationService.add_subscription(
            db_session, student.id, "https://endpoint.example.com", "p256dh", "auth"
        )

        assert subscription.id is not None
        assert subscription.student_id == student.id

    def test_calling_twice_for_same_endpoint_creates_two_rows(self, db_session):
        from app.models import PushSubscription

        student = make_student(db_session)
        db_session.commit()

        NotificationService.add_subscription(db_session, student.id, "https://endpoint.example.com", "p1", "a1")
        NotificationService.add_subscription(db_session, student.id, "https://endpoint.example.com", "p2", "a2")

        count = db_session.query(PushSubscription).filter(PushSubscription.student_id == student.id).count()
        assert count == 2


class TestGetHistory:
    def test_returns_all_notifications_most_recent_first(self, db_session):
        student = make_student(db_session)
        db_session.commit()
        older = make_notification(db_session, student_id=student.id, reference_id="ref-old")
        newer = make_notification(db_session, student_id=student.id, reference_id="ref-new")
        db_session.commit()

        history = NotificationService.get_history(db_session, student.id)

        assert [n.id for n in history] == [newer.id, older.id]

    def test_excludes_another_students_notifications(self, db_session):
        student_a = make_student(db_session)
        student_b = make_student(db_session)
        db_session.commit()
        make_notification(db_session, student_id=student_a.id)
        db_session.commit()

        history = NotificationService.get_history(db_session, student_b.id)

        assert history == []


class TestMarkRead:
    def test_sets_read_at_on_first_call(self, db_session):
        student = make_student(db_session)
        db_session.commit()
        notification = make_notification(db_session, student_id=student.id)
        db_session.commit()

        result = NotificationService.mark_read(db_session, notification.id, student.id)

        assert result.read_at is not None

    def test_second_call_is_a_noop(self, db_session):
        student = make_student(db_session)
        db_session.commit()
        notification = make_notification(db_session, student_id=student.id)
        db_session.commit()

        first = NotificationService.mark_read(db_session, notification.id, student.id)
        first_read_at = first.read_at
        second = NotificationService.mark_read(db_session, notification.id, student.id)

        assert second.read_at == first_read_at

    def test_scoped_to_student_returns_none_for_wrong_student(self, db_session):
        student_a = make_student(db_session)
        student_b = make_student(db_session)
        db_session.commit()
        notification = make_notification(db_session, student_id=student_a.id)
        db_session.commit()

        result = NotificationService.mark_read(db_session, notification.id, student_b.id)

        assert result is None
