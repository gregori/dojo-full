"""Unit tests for report_service.py's four query/aggregation functions (REP-01-REP-04)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.services.report_service import ReportService
from tests.unit.conftest import (
    make_attendance,
    make_belt,
    make_belt_promotion,
    make_event,
    make_event_type,
    make_exam,
    make_exam_participant,
    make_payment,
    make_plan_tier,
    make_plan_version,
    make_student,
    make_student_plan,
)


class TestGetBeltExamReport:
    def test_happy_path_returns_participations_and_promotion_most_recent_first(self, db_session):
        student = make_student(db_session)
        belt = make_belt(db_session)
        older_exam = make_exam(db_session, belt_id=belt.id, exam_date=datetime(2025, 1, 1, tzinfo=UTC))
        newer_exam = make_exam(db_session, belt_id=belt.id, exam_date=datetime(2026, 1, 1, tzinfo=UTC))
        make_exam_participant(db_session, exam_id=older_exam.id, student_id=student.id, status="rejected")
        newer_participant = make_exam_participant(
            db_session, exam_id=newer_exam.id, student_id=student.id, status="approved"
        )
        make_belt_promotion(
            db_session,
            student_id=student.id,
            belt_id=belt.id,
            exam_id=newer_participant.exam_id,
            promoted_at=datetime(2026, 1, 2, tzinfo=UTC),
        )

        report = ReportService.get_belt_exam_report(db_session, student.id)

        assert report["student_id"] == student.id
        assert len(report["participations"]) == 2
        assert report["participations"][0]["exam_id"] == newer_exam.id
        assert report["participations"][0]["status"] == "approved"
        assert report["participations"][0]["promoted_at"] is not None
        assert report["participations"][1]["exam_id"] == older_exam.id
        assert report["participations"][1]["promoted_at"] is None

    def test_404_for_nonexistent_student(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            ReportService.get_belt_exam_report(db_session, "nonexistent-id")

        assert exc_info.value.status_code == 404

    def test_empty_list_for_student_with_no_participations(self, db_session):
        student = make_student(db_session)

        report = ReportService.get_belt_exam_report(db_session, student.id)

        assert report["participations"] == []


class TestGetStudentAttendanceReport:
    def test_happy_path_counts_and_orders_attendances_in_range(self, db_session):
        student = make_student(db_session)
        event_type = make_event_type(db_session, name="Regular")
        event = make_event(db_session, event_type_id=event_type.id, title="Aula de Terça")
        make_attendance(
            db_session, event_id=event.id, student_id=student.id, check_in_at=datetime(2026, 1, 10, tzinfo=UTC)
        )

        report = ReportService.get_student_attendance_report(
            db_session,
            student.id,
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 1, 31, tzinfo=UTC),
        )

        assert report["total_attendances"] == 1
        assert report["attendances"][0]["event_title"] == "Aula de Terça"
        assert report["attendances"][0]["event_type_name"] == "Regular"

    def test_404_for_nonexistent_student(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            ReportService.get_student_attendance_report(db_session, "nonexistent-id")

        assert exc_info.value.status_code == 404

    def test_400_when_start_date_after_end_date(self, db_session):
        student = make_student(db_session)

        with pytest.raises(HTTPException) as exc_info:
            ReportService.get_student_attendance_report(
                db_session,
                student.id,
                start_date=datetime(2026, 2, 1, tzinfo=UTC),
                end_date=datetime(2026, 1, 1, tzinfo=UTC),
            )

        assert exc_info.value.status_code == 400

    def test_empty_range_returns_empty_list_and_zero_total(self, db_session):
        student = make_student(db_session)

        report = ReportService.get_student_attendance_report(
            db_session,
            student.id,
            start_date=datetime(2020, 1, 1, tzinfo=UTC),
            end_date=datetime(2020, 1, 31, tzinfo=UTC),
        )

        assert report["total_attendances"] == 0
        assert report["attendances"] == []


class TestGetClassAttendanceReport:
    def test_happy_path_returns_event_counts_and_roster(self, db_session):
        event_type = make_event_type(db_session, name="Yudansha")
        event = make_event(
            db_session, event_type_id=event_type.id, title="Treino", start_datetime=datetime(2026, 1, 10, tzinfo=UTC)
        )
        student = make_student(db_session)
        make_attendance(
            db_session, event_id=event.id, student_id=student.id, check_in_at=datetime(2026, 1, 10, tzinfo=UTC)
        )

        report = ReportService.get_class_attendance_report(
            db_session,
            event_type.id,
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 1, 31, tzinfo=UTC),
        )

        assert report["event_type_name"] == "Yudansha"
        assert len(report["events"]) == 1
        assert report["events"][0]["attendance_count"] == 1
        assert len(report["roster"]) == 1
        assert report["roster"][0]["student_id"] == student.id
        assert report["roster"][0]["total_attendances"] == 1

    def test_404_for_nonexistent_event_type(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            ReportService.get_class_attendance_report(db_session, "nonexistent-id")

        assert exc_info.value.status_code == 404

    def test_400_when_start_date_after_end_date(self, db_session):
        event_type = make_event_type(db_session)

        with pytest.raises(HTTPException) as exc_info:
            ReportService.get_class_attendance_report(
                db_session,
                event_type.id,
                start_date=datetime(2026, 2, 1, tzinfo=UTC),
                end_date=datetime(2026, 1, 1, tzinfo=UTC),
            )

        assert exc_info.value.status_code == 400

    def test_empty_range_returns_empty_events_and_roster(self, db_session):
        event_type = make_event_type(db_session)

        report = ReportService.get_class_attendance_report(
            db_session,
            event_type.id,
            start_date=datetime(2020, 1, 1, tzinfo=UTC),
            end_date=datetime(2020, 1, 31, tzinfo=UTC),
        )

        assert report["events"] == []
        assert report["roster"] == []

    def test_roster_excludes_student_with_zero_attendances_in_range(self, db_session):
        """Regression: only students with >=1 attendance in range appear (no zero-attendance rows)."""
        event_type = make_event_type(db_session)
        attended_event = make_event(
            db_session, event_type_id=event_type.id, start_datetime=datetime(2026, 1, 10, tzinfo=UTC)
        )
        attending_student = make_student(db_session)
        other_student = make_student(db_session)
        make_attendance(
            db_session,
            event_id=attended_event.id,
            student_id=attending_student.id,
            check_in_at=datetime(2026, 1, 10, tzinfo=UTC),
        )
        # other_student never attended this event type -- must not appear in the roster.

        report = ReportService.get_class_attendance_report(
            db_session,
            event_type.id,
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 1, 31, tzinfo=UTC),
        )

        roster_student_ids = {item["student_id"] for item in report["roster"]}
        assert attending_student.id in roster_student_ids
        assert other_student.id not in roster_student_ids


class TestGetFinancialReport:
    def test_happy_path_returns_all_three_sections(self, db_session):
        student = make_student(db_session, is_active=True, classes_per_week=2)
        tier = make_plan_tier(db_session, weekly_frequency=2)
        version = make_plan_version(db_session, plan_tier_id=tier.id, price=Decimal("150.00"))
        make_student_plan(db_session, student_id=student.id, plan_version_id=version.id)
        make_payment(
            db_session, student_id=student.id, amount=Decimal("150.00"), payment_date=datetime(2026, 1, 5, tzinfo=UTC)
        )

        report = ReportService.get_financial_report(
            db_session,
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 1, 31, tzinfo=UTC),
            months_ahead=3,
        )

        assert len(report["payments"]) == 1
        assert report["payments"][0]["amount"] == Decimal("150.00")
        assert isinstance(report["delinquency"], list)
        assert report["projection"]["monthly_total"] == Decimal("150.00")
        assert report["projection"]["months_ahead"] == 3
        assert report["projection"]["projected_total"] == Decimal("450.00")

    def test_400_when_start_date_after_end_date(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            ReportService.get_financial_report(
                db_session,
                start_date=datetime(2026, 2, 1, tzinfo=UTC),
                end_date=datetime(2026, 1, 1, tzinfo=UTC),
            )

        assert exc_info.value.status_code == 400

    def test_400_when_months_ahead_below_minimum(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            ReportService.get_financial_report(db_session, months_ahead=0)

        assert exc_info.value.status_code == 400

    def test_empty_data_returns_zero_totals(self, db_session):
        report = ReportService.get_financial_report(
            db_session,
            start_date=datetime(2020, 1, 1, tzinfo=UTC),
            end_date=datetime(2020, 1, 31, tzinfo=UTC),
        )

        assert report["payments"] == []
        assert report["delinquency"] == []
        assert report["projection"]["monthly_total"] == Decimal("0")
        assert report["projection"]["projected_total"] == Decimal("0")

    def test_projection_math_has_no_delinquency_adjustment(self, db_session):
        """Regression: projection is a flat monthly_total * months_ahead, no adjustment."""
        student_a = make_student(db_session, is_active=True)
        student_b = make_student(db_session, is_active=True)
        tier = make_plan_tier(db_session)
        version = make_plan_version(db_session, plan_tier_id=tier.id, price=Decimal("100.00"))
        make_student_plan(db_session, student_id=student_a.id, plan_version_id=version.id)
        make_student_plan(db_session, student_id=student_b.id, plan_version_id=version.id)

        report = ReportService.get_financial_report(db_session, months_ahead=6)

        assert report["projection"]["monthly_total"] == Decimal("200.00")
        assert report["projection"]["projected_total"] == Decimal("1200.00")


class TestDateRangeDefaults:
    def test_omitted_range_defaults_to_current_calendar_month(self, db_session):
        student = make_student(db_session)

        report = ReportService.get_student_attendance_report(db_session, student.id)

        # No exception raised, and the function ran with a defaulted range.
        assert report["total_attendances"] == 0
        assert report["attendances"] == []


class TestDateRangeAlwaysSameTimezoneHandling:
    def test_naive_datetimes_do_not_raise_when_compared(self, db_session):
        student = make_student(db_session)

        # start_date/end_date without tzinfo must not raise a naive/aware comparison error.
        report = ReportService.get_student_attendance_report(
            db_session,
            student.id,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )

        assert report["attendances"] == []


def test_module_helper_range_boundaries_are_inclusive(db_session):
    student = make_student(db_session)
    event = make_event(db_session)
    boundary = datetime(2026, 1, 15, tzinfo=UTC)
    make_attendance(db_session, event_id=event.id, student_id=student.id, check_in_at=boundary)

    report = ReportService.get_student_attendance_report(
        db_session, student.id, start_date=boundary, end_date=boundary + timedelta(days=1)
    )

    assert report["total_attendances"] == 1
