"""Unit tests for recording and soft-voiding payments."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.services import PaymentService
from tests.unit.conftest import make_student, make_user


class TestRecordPayment:
    def test_records_active_payment(self, db_session):
        student = make_student(db_session)
        user = make_user(db_session)

        payment = PaymentService.record_payment(
            db_session, student.id, Decimal("100.00"), datetime.now(UTC), "pix", recorded_by=user.id
        )

        assert payment.status == "active"
        assert payment.amount == Decimal("100.00")
        assert payment.recorded_by == user.id

    def test_unknown_student_raises_404(self, db_session):
        user = make_user(db_session)

        with pytest.raises(HTTPException) as exc_info:
            PaymentService.record_payment(
                db_session, "missing-student-id", Decimal("100.00"), datetime.now(UTC), None, recorded_by=user.id
            )

        assert exc_info.value.status_code == 404


class TestVoidPayment:
    def test_voids_payment_with_audit_trail(self, db_session):
        student = make_student(db_session)
        user = make_user(db_session)
        voider = make_user(db_session)
        payment = PaymentService.record_payment(
            db_session, student.id, Decimal("100.00"), datetime.now(UTC), None, recorded_by=user.id
        )

        voided = PaymentService.void_payment(db_session, payment.id, voided_by=voider.id)

        assert voided.status == "voided"
        assert voided.voided_at is not None
        assert voided.voided_by == voider.id

    def test_voiding_already_voided_payment_raises_400(self, db_session):
        student = make_student(db_session)
        user = make_user(db_session)
        payment = PaymentService.record_payment(
            db_session, student.id, Decimal("100.00"), datetime.now(UTC), None, recorded_by=user.id
        )
        PaymentService.void_payment(db_session, payment.id, voided_by=user.id)

        with pytest.raises(HTTPException) as exc_info:
            PaymentService.void_payment(db_session, payment.id, voided_by=user.id)

        assert exc_info.value.status_code == 400

    def test_unknown_payment_raises_404(self, db_session):
        user = make_user(db_session)

        with pytest.raises(HTTPException) as exc_info:
            PaymentService.void_payment(db_session, "missing-payment-id", voided_by=user.id)

        assert exc_info.value.status_code == 404
