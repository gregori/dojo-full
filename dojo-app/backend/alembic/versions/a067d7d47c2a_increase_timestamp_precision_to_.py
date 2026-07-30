"""Increase timestamp precision to microseconds to fix ordering flakiness.

Revision ID: a067d7d47c2a
Revises: a2e0a753d11c
Create Date: 2026-07-29 23:12:55.128446

"""

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision = "a067d7d47c2a"
down_revision = "a2e0a753d11c"
branch_labels = None
depends_on = None

# Every table using TimestampMixin (all UUIDMixin+TimestampMixin models except
# BeltRequirement, which only has UUIDMixin and no created_at/updated_at).
_TABLES = [
    "organizations",
    "dojos",
    "users",
    "belts",
    "event_types",
    "students",
    "event_series",
    "events",
    "attendances",
    "pre_checkins",
    "documents",
    "medical_exams",
    "plan_tiers",
    "plan_versions",
    "student_plans",
    "mensalidades",
    "payments",
    "contract_template_versions",
    "contracts",
    "exams",
    "exam_participants",
    "exam_board_members",
    "belt_promotions",
]


def upgrade() -> None:
    """Widen created_at/updated_at from whole-second DATETIME to DATETIME(6).

    Existing values keep their (zero) fractional seconds; only future writes
    gain microsecond precision, matching what datetime.now() already
    produces in Python.
    """
    for table in _TABLES:
        op.alter_column(table, "created_at", type_=mysql.DATETIME(fsp=6), existing_nullable=False)
        op.alter_column(table, "updated_at", type_=mysql.DATETIME(fsp=6), existing_nullable=False)


def downgrade() -> None:
    for table in _TABLES:
        op.alter_column(table, "created_at", type_=sa.DateTime(), existing_nullable=False)
        op.alter_column(table, "updated_at", type_=sa.DateTime(), existing_nullable=False)
