"""
create orgs table

Revision ID: 001
Revises: None
Create Date: 2025-01-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orgs",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_orgs_id", "orgs", ["id"])

    # Seed default organization (idempotent via INSERT IGNORE)
    op.execute(
        "INSERT IGNORE INTO orgs (id, name, created_at, updated_at) "
        "VALUES ('00000000-0000-0000-0000-000000000001', 'Default Dojo', NOW(), NOW())"
    )


def downgrade() -> None:
    op.drop_index("ix_orgs_id", table_name="orgs")
    op.drop_table("orgs")
