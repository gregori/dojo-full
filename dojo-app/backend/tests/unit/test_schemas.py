"""Unit tests for app.schemas validation."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.attendance import AttendanceCreate, CheckInQRRequest, CheckInRequest
from app.schemas.belt import BeltCreate, BeltRequirementCreate, BeltUpdate
from app.schemas.event import EventCreate, EventTypeCreate, EventUpdate
from app.schemas.exam import ExamBoardMemberCreate, ExamCreate, ExamParticipantCreate
from app.schemas.organization import DojoCreate, OrganizationCreate
from app.schemas.student import StudentCreate, StudentUpdate
from app.schemas.user import Token, UserCreate, UserLogin, UserUpdate


class TestUserSchemas:
    """Tests for User schema validation."""

    def test_user_create_valid(self):
        """Should create UserCreate with valid data."""
        user = UserCreate(
            email="test@dojo.com",
            password="secret123",
            full_name="Test User",
            role="admin",
        )
        assert user.email == "test@dojo.com"
        assert user.role == "admin"

    def test_user_create_invalid_email(self):
        """Should reject invalid email."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="not-an-email",
                password="secret123",
                full_name="Test User",
                role="admin",
            )

    def test_user_update_partial(self):
        """Should allow partial updates with UserUpdate."""
        update = UserUpdate(full_name="New Name")
        assert update.full_name == "New Name"
        assert update.email is None
        assert update.password is None

    def test_user_login(self):
        """Should create UserLogin with username and password."""
        login = UserLogin(username="test@dojo.com", password="pass")
        assert login.username == "test@dojo.com"

    def test_token_schema(self):
        """Should create Token with access_token and type."""
        token = Token(access_token="abc123", token_type="bearer")
        assert token.access_token == "abc123"
        assert token.token_type == "bearer"


class TestStudentSchemas:
    """Tests for Student schema validation."""

    def test_student_create_minimal(self):
        """Should create StudentCreate with minimal required fields."""
        data = StudentCreate(
            full_name="John Doe",
            category="adult",
            current_belt_id="belt-123",
            pin="1234",
        )
        assert data.full_name == "John Doe"
        assert data.pin == "1234"
        assert data.registration_number is None

    def test_student_create_with_registration(self):
        """Should accept optional registration_number."""
        data = StudentCreate(
            full_name="Jane Doe",
            category="child",
            current_belt_id="belt-456",
            pin="5678",
            registration_number="REG001",
        )
        assert data.registration_number == "REG001"

    def test_student_update_partial(self):
        """Should allow partial updates."""
        update = StudentUpdate(full_name="Updated Name")
        assert update.full_name == "Updated Name"
        assert update.email is None


class TestEventSchemas:
    """Tests for Event schema validation."""

    def test_event_create_valid(self):
        """Should create EventCreate with valid data."""
        data = EventCreate(
            title="Test Event",
            event_type_id="et-123",
            start_datetime=datetime.now(UTC),
        )
        assert data.title == "Test Event"

    def test_event_create_invalid_dates(self):
        """Should reject end_datetime before start_datetime."""
        with pytest.raises(ValidationError):
            EventCreate(
                title="Bad Event",
                event_type_id="et-123",
                start_datetime=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
                end_datetime=datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
            )

    def test_event_create_valid_dates(self):
        """Should accept end_datetime after start_datetime."""
        data = EventCreate(
            title="Good Event",
            event_type_id="et-123",
            start_datetime=datetime(2025, 6, 1, 9, 0, tzinfo=UTC),
            end_datetime=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
        )
        assert data.end_datetime is not None

    def test_event_type_create(self):
        """Should create EventTypeCreate."""
        data = EventTypeCreate(name="Class", color="#ff0000", counts_for_belt=True)
        assert data.name == "Class"
        assert data.counts_for_belt is True

    def test_event_type_create_defaults(self):
        """Should default counts_for_belt to True."""
        data = EventTypeCreate(name="Class")
        assert data.counts_for_belt is True

    def test_event_update_partial(self):
        """Should allow partial updates."""
        update = EventUpdate(title="Updated")
        assert update.title == "Updated"
        assert update.status is None


class TestAttendanceSchemas:
    """Tests for Attendance schema validation."""

    def test_check_in_request(self):
        """Should create CheckInRequest."""
        data = CheckInRequest(registration_number="001", pin="1234")
        assert data.registration_number == "001"
        assert data.check_in_method == "tablet"  # default

    def test_check_in_request_custom_method(self):
        """Should accept custom check_in_method."""
        data = CheckInRequest(registration_number="001", pin="1234", check_in_method="qrcode")
        assert data.check_in_method == "qrcode"

    def test_check_in_qr_request(self):
        """Should create CheckInQRRequest."""
        data = CheckInQRRequest(registration_number="001", pin="1234", check_in_token="token-abc")
        assert data.check_in_token == "token-abc"

    def test_attendance_create(self):
        """Should create AttendanceCreate."""
        data = AttendanceCreate(
            event_id="evt-1",
            student_id="stu-1",
            check_in_method="manual",
            registered_by="user-1",
        )
        assert data.check_in_method == "manual"


class TestBeltSchemas:
    """Tests for Belt schema validation."""

    def test_belt_create(self):
        """Should create BeltCreate."""
        data = BeltCreate(name="Yellow", category="adult", sort_order=3)
        assert data.name == "Yellow"
        assert data.sort_order == 3

    def test_belt_update_partial(self):
        """Should allow partial updates."""
        update = BeltUpdate(name="Gold")
        assert update.name == "Gold"
        assert update.sort_order is None

    def test_belt_requirement_create(self):
        """Should create BeltRequirementCreate."""
        data = BeltRequirementCreate(
            event_type_id="et-1",
            required_count=20,
            description="Regular classes",
        )
        assert data.required_count == 20


class TestExamSchemas:
    """Tests for Exam schema validation."""

    def test_exam_create(self):
        """Should create ExamCreate."""
        data = ExamCreate(
            event_id="evt-1",
            belt_id="belt-1",
            exam_date=datetime.now(UTC),
        )
        assert data.event_id == "evt-1"

    def test_exam_participant_create(self):
        """Should create ExamParticipantCreate."""
        data = ExamParticipantCreate(
            student_id="stu-1",
            role="candidate",
        )
        assert data.role == "candidate"
        assert data.override_eligibility is False

    def test_exam_participant_create_with_override(self):
        """Should accept override fields."""
        data = ExamParticipantCreate(
            student_id="stu-1",
            role="candidate",
            override_eligibility=True,
            override_reason="Special case",
        )
        assert data.override_eligibility is True
        assert data.override_reason == "Special case"

    def test_exam_board_member_create(self):
        """Should create ExamBoardMemberCreate."""
        data = ExamBoardMemberCreate(
            user_id="user-1",
            role_in_board="president",
        )
        assert data.role_in_board == "president"

    def test_exam_board_member_create_default_role(self):
        """Should default role_in_board to 'member'."""
        data = ExamBoardMemberCreate(user_id="user-1")
        assert data.role_in_board == "member"


class TestOrganizationSchemas:
    """Tests for Organization schema validation."""

    def test_organization_create(self):
        """Should create OrganizationCreate."""
        data = OrganizationCreate(name="Test Org", description="A test org")
        assert data.name == "Test Org"

    def test_dojo_create(self):
        """Should create DojoCreate."""
        data = DojoCreate(
            organization_id="org-1",
            code=1,
            name="Main Dojo",
            address="123 Main St",
        )
        assert data.name == "Main Dojo"
        assert data.code == 1
