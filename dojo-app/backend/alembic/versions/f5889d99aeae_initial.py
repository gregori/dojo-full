"""Initial migration.

Revision ID: f5889d99aeae
Revises:
Create Date: 2026-06-02 18:50:35.275887

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f5889d99aeae"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the baseline schema."""
    op.create_table(
        "event_types",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("counts_for_belt", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "organizations",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "belts",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.Enum("child", "adult", name="belt_category"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "dojos",
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "belt_requirements",
        sa.Column("belt_id", sa.String(length=36), nullable=False),
        sa.Column("event_type_id", sa.String(length=36), nullable=False),
        sa.Column("required_count", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["belt_id"], ["belts.id"]),
        sa.ForeignKeyConstraint(["event_type_id"], ["event_types.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "students",
        sa.Column("registration_number", sa.String(length=50), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("birth_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("category", sa.Enum("child", "adult", name="student_category"), nullable=False),
        sa.Column("current_belt_id", sa.String(length=36), nullable=False),
        sa.Column("dojo_id", sa.String(length=36), nullable=True),
        sa.Column("pin", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("contract_name", sa.String(length=255), nullable=True),
        sa.Column("contract_cpf", sa.String(length=14), nullable=True),
        sa.Column("address_street", sa.String(length=255), nullable=True),
        sa.Column("address_neighborhood", sa.String(length=100), nullable=True),
        sa.Column("address_city", sa.String(length=100), nullable=True),
        sa.Column("address_zip", sa.String(length=10), nullable=True),
        sa.Column("classes_per_week", sa.Integer(), nullable=True),
        sa.Column("class_days", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["current_belt_id"], ["belts.id"]),
        sa.ForeignKeyConstraint(["dojo_id"], ["dojos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("registration_number"),
    )
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("instructor", "admin", name="user_role"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=True),
        sa.Column("dojo_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dojo_id"], ["dojos.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "events",
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("event_type_id", sa.String(length=36), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=True),
        sa.Column("check_in_token", sa.String(length=36), nullable=False),
        sa.Column(
            "status",
            sa.Enum("scheduled", "in_progress", "finished", "cancelled", name="event_status"),
            nullable=False,
        ),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["event_type_id"], ["event_types.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "attendances",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("check_in_method", sa.Enum("tablet", "qrcode", "manual", name="check_in_method"), nullable=False),
        sa.Column("check_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registered_by", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["registered_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "exams",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("belt_id", sa.String(length=36), nullable=False),
        sa.Column("exam_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("scheduled", "in_progress", "completed", "cancelled", name="exam_status"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["belt_id"], ["belts.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_table(
        "belt_promotions",
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("belt_id", sa.String(length=36), nullable=False),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("promoted_by", sa.String(length=36), nullable=True),
        sa.Column("exam_id", sa.String(length=36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["belt_id"], ["belts.id"]),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"]),
        sa.ForeignKeyConstraint(["promoted_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "exam_board_members",
        sa.Column("exam_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role_in_board", sa.Enum("president", "member", name="board_role"), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "exam_participants",
        sa.Column("exam_id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.Enum("candidate", "uke", name="exam_participant_role"), nullable=False),
        sa.Column("status", sa.Enum("pending", "approved", "rejected", name="exam_participant_status"), nullable=False),
        sa.Column("is_eligible", sa.Boolean(), nullable=False),
        sa.Column("override_eligibility", sa.Boolean(), nullable=False),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("overridden_by", sa.String(length=36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"]),
        sa.ForeignKeyConstraint(["overridden_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop the baseline schema."""
    op.drop_table("exam_participants")
    op.drop_table("exam_board_members")
    op.drop_table("belt_promotions")
    op.drop_table("exams")
    op.drop_table("attendances")
    op.drop_table("events")
    op.drop_table("users")
    op.drop_table("students")
    op.drop_table("belt_requirements")
    op.drop_table("dojos")
    op.drop_table("belts")
    op.drop_table("organizations")
    op.drop_table("event_types")
