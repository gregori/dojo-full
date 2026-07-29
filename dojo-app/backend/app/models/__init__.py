import uuid
from datetime import UTC, date, datetime, time, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
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
    pre_checkins: Mapped[list["PreCheckIn"]] = relationship(back_populates="student")
    exam_participations: Mapped[list["ExamParticipant"]] = relationship(back_populates="student")
    belt_promotions: Mapped[list["BeltPromotion"]] = relationship(back_populates="student")
    documents: Mapped[list["Document"]] = relationship(back_populates="student")
    medical_exams: Mapped[list["MedicalExam"]] = relationship(back_populates="student")
    student_plans: Mapped[list["StudentPlan"]] = relationship(back_populates="student")
    mensalidades: Mapped[list["Mensalidade"]] = relationship(back_populates="student")
    payments: Mapped[list["Payment"]] = relationship(back_populates="student")
    contracts: Mapped[list["Contract"]] = relationship(back_populates="student")


class EventSeries(UUIDMixin, TimestampMixin, Base):
    """A recurring weekly class template that produces ordinary Event occurrences.

    Fields mirror Event's own single-occurrence fields (RES-01/RES-03); days_of_week
    is a simple sorted comma-separated string of Monday=0..Sunday=6 integers -- not a
    join table, mirroring Student.class_days's storage simplicity but, unlike
    class_days, machine-parseable (see plan.md ground-truth notes).
    """

    __tablename__ = "event_series"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type_id: Mapped[str] = mapped_column(ForeignKey("event_types.id"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    minimum_belt_id: Mapped[str | None] = mapped_column(ForeignKey("belts.id"), nullable=True)
    days_of_week: Mapped[str] = mapped_column(String(20), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    series_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    series_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    check_in_token: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)

    event_type: Mapped["EventType"] = relationship()
    minimum_belt: Mapped[Belt | None] = relationship(foreign_keys=[minimum_belt_id])
    organization: Mapped[Organization | None] = relationship()
    occurrences: Mapped[list["Event"]] = relationship(back_populates="event_series")


class Event(UUIDMixin, TimestampMixin, Base):
    """Dojo events/classes."""

    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("event_series_id", "occurrence_date", name="uq_events_series_occurrence_date"),)

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
    minimum_belt_id: Mapped[str | None] = mapped_column(ForeignKey("belts.id"), nullable=True)
    event_series_id: Mapped[str | None] = mapped_column(ForeignKey("event_series.id"), nullable=True)
    occurrence_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    event_type: Mapped[EventType] = relationship(back_populates="events")
    organization: Mapped[Organization | None] = relationship(back_populates="events")
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="event")
    pre_checkins: Mapped[list["PreCheckIn"]] = relationship(back_populates="event")
    minimum_belt: Mapped[Belt | None] = relationship(foreign_keys=[minimum_belt_id])
    exam: Mapped[Optional["Exam"]] = relationship(back_populates="event")
    event_series: Mapped[Optional["EventSeries"]] = relationship(back_populates="occurrences")


class Attendance(UUIDMixin, TimestampMixin, Base):
    """Student attendance records."""

    __tablename__ = "attendances"
    __table_args__ = (UniqueConstraint("event_id", "student_id", name="uq_attendances_event_student"),)

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


class PreCheckIn(UUIDMixin, TimestampMixin, Base):
    """A student's pre-check-in intention for a scheduled event, distinct from attendance."""

    __tablename__ = "pre_checkins"
    __table_args__ = (
        UniqueConstraint("event_id", "student_id", name="uq_pre_checkins_event_student"),
        CheckConstraint("status IN ('confirmed', 'cancelled', 'converted')", name="ck_pre_checkins_status"),
    )

    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), nullable=False)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("confirmed", "cancelled", "converted", name="pre_checkin_status"), default="confirmed", nullable=False
    )
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    event: Mapped[Event] = relationship(back_populates="pre_checkins")
    student: Mapped[Student] = relationship(back_populates="pre_checkins")


class Document(UUIDMixin, TimestampMixin, Base):
    """Generic stored-file metadata, reused by medical exams and future document types.

    The application never persists file bytes; only the storage key and
    descriptive metadata are kept here. ``deleted_at``/``deleted_by`` record
    when and by whom a document left the ``active`` state, whether by
    supersession or an explicit soft delete.
    """

    __tablename__ = "documents"
    __table_args__ = (CheckConstraint("status IN ('active', 'superseded', 'deleted')", name="ck_documents_status"),)

    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    uploaded_by_student_self: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(
        Enum("active", "superseded", "deleted", name="document_status"), default="active", nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    student: Mapped[Student] = relationship(back_populates="documents")
    uploaded_by: Mapped[User | None] = relationship(foreign_keys=[uploaded_by_user_id])


class MedicalExam(UUIDMixin, TimestampMixin, Base):
    """A student's medical exam record.

    Append-only history: a new submission supersedes the previous active
    record instead of overwriting it. Exactly one ``active`` record per
    student is enforced at the service layer, not by a database constraint.
    """

    __tablename__ = "medical_exams"
    __table_args__ = (CheckConstraint("status IN ('active', 'superseded')", name="ck_medical_exams_status"),)

    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    exam_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("active", "superseded", name="medical_exam_status"), default="active", nullable=False
    )

    student: Mapped[Student] = relationship(back_populates="medical_exams")
    document: Mapped[Document | None] = relationship()


class PlanTier(UUIDMixin, TimestampMixin, Base):
    """A stable weekly-frequency plan-tier identity (D9: a single global catalog).

    ``is_active`` retires a tier from future assignment without deleting its
    priced history or the mensalidades already generated against it.
    """

    __tablename__ = "plan_tiers"

    weekly_frequency: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    versions: Mapped[list["PlanVersion"]] = relationship(back_populates="plan_tier")


class PlanVersion(UUIDMixin, TimestampMixin, Base):
    """A priced, versioned snapshot of a plan tier.

    Editing a tier's price creates a new active version and supersedes the
    previous one (service-layer-enforced, the same append-only-supersession
    pattern as ``MedicalExam``). ``StudentPlan`` locks to one of these, so a
    later catalog edit never reprices an already-assigned student (D11).
    """

    __tablename__ = "plan_versions"
    __table_args__ = (CheckConstraint("status IN ('active', 'superseded')", name="ck_plan_versions_status"),)

    plan_tier_id: Mapped[str] = mapped_column(ForeignKey("plan_tiers.id"), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("active", "superseded", name="plan_version_status"), default="active", nullable=False
    )
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    plan_tier: Mapped[PlanTier] = relationship(back_populates="versions")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])


class StudentPlan(UUIDMixin, TimestampMixin, Base):
    """A student's locked assignment to a ``PlanVersion``.

    Assigning or changing a student's plan creates a new active row and
    supersedes the prior one (single-active-row service pattern); the price
    is locked at assignment time and only changes via explicit reassignment.
    """

    __tablename__ = "student_plans"
    __table_args__ = (CheckConstraint("status IN ('active', 'superseded')", name="ck_student_plans_status"),)

    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    plan_version_id: Mapped[str] = mapped_column(ForeignKey("plan_versions.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("active", "superseded", name="student_plan_status"), default="active", nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    student: Mapped["Student"] = relationship(back_populates="student_plans")
    plan_version: Mapped[PlanVersion] = relationship()


class Mensalidade(UUIDMixin, TimestampMixin, Base):
    """One monthly charge for an active student.

    The amount (including any proration) is computed and frozen at
    generation time and never mutated afterward. There is no stored status
    column (D4): open/partial/paid/overdue is computed on read from a
    student's payments.
    """

    __tablename__ = "mensalidades"
    __table_args__ = (
        UniqueConstraint("student_id", "reference_month", name="uq_mensalidades_student_reference_month"),
    )

    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    plan_version_id: Mapped[str] = mapped_column(ForeignKey("plan_versions.id"), nullable=False)
    reference_month: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    student: Mapped["Student"] = relationship(back_populates="mensalidades")
    plan_version: Mapped[PlanVersion] = relationship()


class Payment(UUIDMixin, TimestampMixin, Base):
    """A payment recorded against a student.

    Not tied to a specific mensalidade by foreign key; allocation across a
    student's open mensalidades is computed on read (FIFO, D7). Soft-voidable,
    mirroring ``Document``'s audit-trailed correction pattern.
    """

    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("status IN ('active', 'voided')", name="ck_payments_status"),)

    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    recorded_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("active", "voided", name="payment_status"), default="active", nullable=False
    )
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    student: Mapped["Student"] = relationship(back_populates="payments")
    recorder: Mapped["User"] = relationship(foreign_keys=[recorded_by])
    voider: Mapped[Optional["User"]] = relationship(foreign_keys=[voided_by])


class ContractTemplateVersion(UUIDMixin, TimestampMixin, Base):
    """A versioned legal contract template body.

    Single versioned lineage (no separate identity table, unlike
    ``PlanTier``/``PlanVersion`` -- there is exactly one template lineage).
    Exactly one ``active`` row at a time, service-layer-enforced.
    """

    __tablename__ = "contract_template_versions"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'superseded')", name="ck_contract_template_versions_status"),
    )

    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("active", "superseded", name="contract_template_version_status"), default="active", nullable=False
    )
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    creator: Mapped["User"] = relationship(foreign_keys=[created_by])


class Contract(UUIDMixin, TimestampMixin, Base):
    """A student's contract, append-only history mirroring ``MedicalExam``'s shape.

    A ``draft`` row is the one pattern in this codebase that is mutably
    edited in place before signing (D7); signing/superseding is append-only
    from that point on, exactly like every other versioned entity here.
    """

    __tablename__ = "contracts"
    __table_args__ = (CheckConstraint("status IN ('draft', 'signed', 'superseded')", name="ck_contracts_status"),)

    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    contract_template_version_id: Mapped[str] = mapped_column(
        ForeignKey("contract_template_versions.id"), nullable=False
    )
    plan_version_id: Mapped[str] = mapped_column(ForeignKey("plan_versions.id"), nullable=False)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    signature_method: Mapped[str | None] = mapped_column(
        Enum("on_screen", "uploaded", name="contract_signature_method"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        Enum("draft", "signed", "superseded", name="contract_status"), default="draft", nullable=False
    )
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    student: Mapped[Student] = relationship(back_populates="contracts")
    contract_template_version: Mapped[ContractTemplateVersion] = relationship()
    plan_version: Mapped[PlanVersion] = relationship()
    document: Mapped[Document | None] = relationship()
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])


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
