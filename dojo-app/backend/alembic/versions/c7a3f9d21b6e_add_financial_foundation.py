"""Add financial foundation: plan tiers, versions, student plans, mensalidades, payments.

Revision ID: c7a3f9d21b6e
Revises: ea64c8751ff2
Create Date: 2026-07-20
"""

import sqlalchemy as sa

from alembic import op

revision = "c7a3f9d21b6e"
down_revision = "ea64c8751ff2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the plan catalog, student plan assignments, mensalidades, and payments tables."""
    op.create_table(
        "plan_tiers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("weekly_frequency", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("weekly_frequency", name="uq_plan_tiers_weekly_frequency"),
    )

    op.create_table(
        "plan_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plan_tier_id", sa.String(length=36), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "superseded", name="plan_version_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'superseded')", name="ck_plan_versions_status"),
        sa.ForeignKeyConstraint(["plan_tier_id"], ["plan_tiers.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plan_versions_tier_status", "plan_versions", ["plan_tier_id", "status"], unique=False)

    op.create_table(
        "student_plans",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("plan_version_id", sa.String(length=36), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "superseded", name="student_plan_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'superseded')", name="ck_student_plans_status"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["plan_version_id"], ["plan_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_student_plans_student_status", "student_plans", ["student_id", "status"], unique=False)

    op.create_table(
        "mensalidades",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("plan_version_id", sa.String(length=36), nullable=False),
        sa.Column("reference_month", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["plan_version_id"], ["plan_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "reference_month", name="uq_mensalidades_student_reference_month"),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("method", sa.String(length=50), nullable=True),
        sa.Column("recorded_by", sa.String(length=36), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "voided", name="payment_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'voided')", name="ck_payments_status"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["voided_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payments_student_id", "payments", ["student_id"], unique=False)


def downgrade() -> None:
    """Remove payments, mensalidades, student plans, plan versions, and plan tiers, in FK-safe order.

    MySQL repoints a FK's supporting index at a composite index sharing its
    leftmost column (dropping the auto-generated single-column one). Restore a
    plain index before dropping the composite one, or the FK is left
    unsupported (same fix as ``ea64c8751ff2``'s downgrade).
    """
    op.drop_table("payments")
    op.drop_table("mensalidades")
    op.create_index("ix_student_plans_student_id", "student_plans", ["student_id"])
    op.drop_index("ix_student_plans_student_status", table_name="student_plans")
    op.drop_table("student_plans")
    op.create_index("ix_plan_versions_plan_tier_id", "plan_versions", ["plan_tier_id"])
    op.drop_index("ix_plan_versions_tier_status", table_name="plan_versions")
    op.drop_table("plan_versions")
    op.drop_table("plan_tiers")
