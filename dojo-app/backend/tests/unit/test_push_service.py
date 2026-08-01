"""Unit tests for PushService: best-effort Web Push delivery to a student's subscriptions."""

from pywebpush import WebPushException

from app.services import PushService
from tests.unit.conftest import make_push_subscription, make_student


class TestSendToStudent:
    def test_calls_webpush_once_per_subscription_with_expected_kwargs(self, db_session, monkeypatch):
        student = make_student(db_session)
        db_session.commit()
        sub1 = make_push_subscription(db_session, student_id=student.id)
        sub2 = make_push_subscription(db_session, student_id=student.id)
        db_session.commit()

        calls = []
        monkeypatch.setattr(
            "app.services.push_service.webpush",
            lambda **kwargs: calls.append(kwargs),
        )

        PushService.send_to_student(db_session, student, "Title", "Body")

        assert len(calls) == 2
        endpoints = {call["subscription_info"]["endpoint"] for call in calls}
        assert endpoints == {sub1.endpoint, sub2.endpoint}
        for call in calls:
            assert "keys" in call["subscription_info"]
            assert set(call["subscription_info"]["keys"]) == {"p256dh", "auth"}
            assert "vapid_private_key" in call
            assert "vapid_claims" in call

    def test_webpush_exception_on_one_subscription_does_not_block_others(self, db_session, monkeypatch):
        student = make_student(db_session)
        db_session.commit()
        make_push_subscription(db_session, student_id=student.id)
        make_push_subscription(db_session, student_id=student.id)
        db_session.commit()

        calls = []

        def fake_webpush(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise WebPushException("delivery failed")

        monkeypatch.setattr("app.services.push_service.webpush", fake_webpush)

        PushService.send_to_student(db_session, student, "Title", "Body")

        assert len(calls) == 2

    def test_zero_subscriptions_makes_zero_calls(self, db_session, monkeypatch):
        student = make_student(db_session)
        db_session.commit()

        calls = []
        monkeypatch.setattr("app.services.push_service.webpush", lambda **kwargs: calls.append(kwargs))

        PushService.send_to_student(db_session, student, "Title", "Body")

        assert calls == []
