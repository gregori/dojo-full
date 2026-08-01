"""Add notification_hub: notifications and push_subscriptions tables.

Revision ID: ad71b8c41d36
Revises: 6c95b3a8815d
Create Date: 2026-07-31 20:24:36.214571

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "ad71b8c41d36"
down_revision = "6c95b3a8815d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the notifications and push_subscriptions tables."""
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column(
            "notification_type",
            sa.Enum("pre_checkin_reminder", "medical_exam_expiring", "mensalidade_due", name="notification_type"),
            nullable=False,
        ),
        sa.Column("reference_id", sa.String(length=36), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id", "notification_type", "reference_id", name="uq_notifications_student_type_reference"
        ),
    )
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("endpoint", sa.String(length=500), nullable=False),
        sa.Column("p256dh_key", sa.String(length=255), nullable=False),
        sa.Column("auth_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop push_subscriptions and notifications."""
    op.drop_table("push_subscriptions")
    op.drop_table("notifications")
