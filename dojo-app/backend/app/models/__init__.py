import uuid
from datetime import UTC, datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class UUIDMixin:
    """Mixin to add UUID primary key."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


class TimestampMixin:
    """Mixin to add created/updated timestamps."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Organization(UUIDMixin, TimestampMixin, Base):
    """Organizations that manage multiple dojos."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    dojos: Mapped[list["Dojo"]] = relationship(back_populates="organization")
    users: Mapped[list["User"]] = relationship(back_populates="organization")
    events: Mapped[list["Event"]] = relationship(back_populates="organization")
    belts: Mapped[list["Belt"]] = relationship(back_populates="organization")


class Dojo(UUIDMixin, TimestampMixin, Base):
    """Individual dojo locations."""

    __tablename__ = "dojos"

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    code: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="dojos")
    students: Mapped[list["Student"]] = relationship(back_populates="dojo")


class User(UUIDMixin, TimestampMixin, Base):
    """System users (instructors and administrators)."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(Enum("instructor", "admin", name="user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    dojo_id: Mapped[str | None] = mapped_column(ForeignKey("dojos.id"), nullable=True)

    organization: Mapped[Organization | None] = relationship(back_populates="users")
    dojo: Mapped[Dojo | None] = relationship()


class Belt(UUIDMixin, TimestampMixin, Base):
    """Martial arts belts/ranks."""

    __tablename__ = "belts"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(Enum("child", "adult", name="belt_category"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)

    # Relationships
    organization: Mapped[Organization | None] = relationship(back_populates="belts")
    students: Mapped[list["Student"]] = relationship(back_populates="current_belt")
    requirements: Mapped[list["BeltRequirement"]] = relationship(back_populates="belt")


class BeltRequirement(UUIDMixin, Base):
    """Requirements for progressing to a specific belt."""

    __tablename__ = "belt_requirements"

    belt_id: Mapped[str] = mapped_column(ForeignKey("belts.id"), nullable=False)
    event_type_id: Mapped[str] = mapped_column(ForeignKey("event_types.id"), nullable=False)
    required_count: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    belt: Mapped[Belt] = relationship(back_populates="requirements")
    event_type: Mapped["EventType"] = relationship(back_populates="requirements")


class EventType(UUIDMixin, TimestampMixin, Base):
    """Types of events (classes, cleaning, exams, etc.)."""

    __tablename__ = "event_types"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    counts_for_belt: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    events: Mapped[list["Event"]] = relationship(back_populates="event_type")
    requirements: Mapped[list[BeltRequirement]] = relationship(back_populates="event_type")


class Student(UUIDMixin, TimestampMixin, Base):
    """Dojo students/athletes."""

    __tablename__ = "students"

    registration_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    birth_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    category: Mapped[str] = mapped_column(Enum("child", "adult", name="student_category"), nullable=False)
    current_belt_id: Mapped[str] = mapped_column(ForeignKey("belts.id"), nullable=False)
    dojo_id: Mapped[str | None] = mapped_column(ForeignKey("dojos.id"), nullable=True)
    pin: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    contract_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contract_cpf: Mapped[str | None] = mapped_column(String(14), nullable=True)
    address_street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_neighborhood: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_zip: Mapped[str | None] = mapped_column(String(10), nullable=True)
    classes_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True, default=2)
    class_days: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    current_belt: Mapped[Belt] = relationship(back_populates="students")
    dojo: Mapped[Dojo | None] = relationship(back_populates="students")
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="student")
    exam_participations: Mapped[list["ExamParticipant"]] = relationship(back_populates="student")
    belt_promotions: Mapped[list["BeltPromotion"]] = relationship(back_populates="student")


class Event(UUIDMixin, TimestampMixin, Base):
    """Dojo events/classes."""

    __tablename__ = "events"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type_id: Mapped[str] = mapped_column(ForeignKey("event_types.id"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    check_in_token: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(
        Enum("scheduled", "in_progress", "finished", "cancelled", name="event_status"),
        default="scheduled",
    )

    # Relationships
    event_type: Mapped[EventType] = relationship(back_populates="events")
    organization: Mapped[Organization | None] = relationship(back_populates="events")
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="event")
    exam: Mapped[Optional["Exam"]] = relationship(back_populates="event")


class Attendance(UUIDMixin, TimestampMixin, Base):
    """Student attendance records."""

    __tablename__ = "attendances"

    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), nullable=False)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    check_in_method: Mapped[str] = mapped_column(
        Enum("tablet", "qrcode", "manual", name="check_in_method"), nullable=False
    )
    check_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    registered_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Relationships
    event: Mapped[Event] = relationship(back_populates="attendances")
    student: Mapped[Student] = relationship(back_populates="attendances")


class Exam(UUIDMixin, TimestampMixin, Base):
    """Belt promotion exams."""

    __tablename__ = "exams"

    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), unique=True, nullable=False)
    belt_id: Mapped[str] = mapped_column(ForeignKey("belts.id"), nullable=False)
    exam_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("scheduled", "in_progress", "completed", "cancelled", name="exam_status"),
        default="scheduled",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Relationships
    event: Mapped[Event] = relationship(back_populates="exam")
    belt: Mapped[Belt] = relationship()
    participants: Mapped[list["ExamParticipant"]] = relationship(back_populates="exam")
    board_members: Mapped[list["ExamBoardMember"]] = relationship(back_populates="exam")


class ExamParticipant(UUIDMixin, TimestampMixin, Base):
    """Students participating in an exam (candidates or ukes)."""

    __tablename__ = "exam_participants"

    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id"), nullable=False)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    role: Mapped[str] = mapped_column(Enum("candidate", "uke", name="exam_participant_role"), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("pending", "approved", "rejected", name="exam_participant_status"),
        default="pending",
    )
    is_eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    override_eligibility: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    overridden_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    exam: Mapped[Exam] = relationship(back_populates="participants")
    student: Mapped[Student] = relationship(back_populates="exam_participations")
    overridden_by_user: Mapped[User | None] = relationship(foreign_keys=[overridden_by])


class ExamBoardMember(UUIDMixin, TimestampMixin, Base):
    """Members of the exam evaluation board."""

    __tablename__ = "exam_board_members"

    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    role_in_board: Mapped[str] = mapped_column(Enum("president", "member", name="board_role"), default="member")

    # Relationships
    exam: Mapped[Exam] = relationship(back_populates="board_members")
    user: Mapped[User] = relationship()


class BeltPromotion(UUIDMixin, TimestampMixin, Base):
    """Record of a student's belt promotion history."""

    __tablename__ = "belt_promotions"

    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    belt_id: Mapped[str] = mapped_column(ForeignKey("belts.id"), nullable=False)
    promoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    promoted_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    exam_id: Mapped[str | None] = mapped_column(ForeignKey("exams.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    student: Mapped[Student] = relationship(back_populates="belt_promotions")
    belt: Mapped[Belt] = relationship()
    promoter: Mapped[User | None] = relationship(foreign_keys=[promoted_by])
    exam: Mapped[Exam | None] = relationship()
