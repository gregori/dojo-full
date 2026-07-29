"""Add event_series: recurring weekly class templates and their Event occurrences.

Revision ID: 6c95b3a8815d
Revises: 56d1afc5972f
Create Date: 2026-07-28 00:46:43.174815

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "6c95b3a8815d"
down_revision = "56d1afc5972f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create event_series and add the event_series_id/occurrence_date columns to events."""
    op.create_table(
        "event_series",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("event_type_id", sa.String(length=36), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("minimum_belt_id", sa.String(length=36), nullable=True),
        sa.Column("days_of_week", sa.String(length=20), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("series_start_date", sa.Date(), nullable=False),
        sa.Column("series_end_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("check_in_token", sa.String(length=36), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_type_id"], ["event_types.id"]),
        sa.ForeignKeyConstraint(["minimum_belt_id"], ["belts.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_series_check_in_token", "event_series", ["check_in_token"], unique=True)

    op.add_column("events", sa.Column("event_series_id", sa.String(length=36), nullable=True))
    op.add_column("events", sa.Column("occurrence_date", sa.Date(), nullable=True))
    op.create_foreign_key("fk_events_event_series_id", "events", "event_series", ["event_series_id"], ["id"])
    op.create_unique_constraint("uq_events_series_occurrence_date", "events", ["event_series_id", "occurrence_date"])


def downgrade() -> None:
    """Drop the event_series_id/occurrence_date columns and the event_series table.

    MySQL repoints a FK's supporting index at a composite index sharing its
    leftmost column (dropping the auto-generated single-column one). Restore a
    plain index before dropping the composite one, or the FK is left
    unsupported (same fix as ``56d1afc5972f``'s/``ea64c8751ff2``'s downgrades).
    """
    op.create_index("ix_events_event_series_id", "events", ["event_series_id"])
    op.drop_constraint("uq_events_series_occurrence_date", "events", type_="unique")
    op.drop_constraint("fk_events_event_series_id", "events", type_="foreignkey")
    op.drop_column("events", "occurrence_date")
    op.drop_column("events", "event_series_id")
    op.drop_index("ix_event_series_check_in_token", table_name="event_series")
    op.drop_table("event_series")
