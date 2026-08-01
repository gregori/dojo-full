"""Link event series to dojo instead of free text location.

Revision ID: a2e0a753d11c
Revises: 6c95b3a8815d
Create Date: 2026-07-29 22:24:03.631841

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a2e0a753d11c"
down_revision = "6c95b3a8815d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Replace event_series.location (free text) with dojo_id (FK to dojos)."""
    op.add_column("event_series", sa.Column("dojo_id", sa.String(length=36), nullable=True))
    op.create_foreign_key("fk_event_series_dojo_id", "event_series", "dojos", ["dojo_id"], ["id"])
    op.drop_column("event_series", "location")


def downgrade() -> None:
    op.add_column("event_series", sa.Column("location", sa.String(length=255), nullable=True))
    op.drop_constraint("fk_event_series_dojo_id", "event_series", type_="foreignkey")
    op.drop_column("event_series", "dojo_id")
