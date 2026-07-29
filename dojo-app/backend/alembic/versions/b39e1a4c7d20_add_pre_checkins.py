"""Add pre-check-ins and event belt eligibility.

Revision ID: b39e1a4c7d20
Revises: f5889d99aeae
Create Date: 2026-07-19
"""

import sqlalchemy as sa

from alembic import op

revision = "b39e1a4c7d20"
down_revision = "f5889d99aeae"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the pre-check-in lifecycle table and optional belt threshold."""
    op.create_unique_constraint("uq_attendances_event_student", "attendances", ["event_id", "student_id"])
    op.add_column("events", sa.Column("minimum_belt_id", sa.String(length=36), nullable=True))
    op.create_foreign_key("fk_events_minimum_belt_id_belts", "events", "belts", ["minimum_belt_id"], ["id"])
    op.create_table(
        "pre_checkins",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column(
            "status",
            sa.Enum("confirmed", "cancelled", "converted", name="pre_checkin_status"),
            nullable=False,
            server_default="confirmed",
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('confirmed', 'cancelled', 'converted')", name="ck_pre_checkins_status"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "student_id", name="uq_pre_checkins_event_student"),
    )
    op.create_index("ix_pre_checkins_event_status", "pre_checkins", ["event_id", "status"], unique=False)


def downgrade() -> None:
    """Remove the pre-check-in table and event belt threshold."""
    op.drop_index("ix_pre_checkins_event_status", table_name="pre_checkins")
    op.drop_table("pre_checkins")
    op.drop_constraint("fk_events_minimum_belt_id_belts", "events", type_="foreignkey")
    op.drop_column("events", "minimum_belt_id")
    # MySQL drops the auto-generated single-column FK index on attendances.event_id
    # when the composite unique index is added, then repoints the FK at it. Restore
    # a plain index before dropping the unique constraint or the FK is left unsupported.
    op.create_index("ix_attendances_event_id", "attendances", ["event_id"])
    op.drop_constraint("uq_attendances_event_student", "attendances", type_="unique")
