"""Add contracts: contract template versions and per-student contracts.

Revision ID: 56d1afc5972f
Revises: c7a3f9d21b6e
Create Date: 2026-07-22
"""

import sqlalchemy as sa

from alembic import op

revision = "56d1afc5972f"
down_revision = "c7a3f9d21b6e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the contract template version history and the per-student contracts table."""
    op.create_table(
        "contract_template_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "superseded", name="contract_template_version_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'superseded')", name="ck_contract_template_versions_status"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "contracts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("contract_template_version_id", sa.String(length=36), nullable=False),
        sa.Column("plan_version_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=True),
        sa.Column(
            "signature_method",
            sa.Enum("on_screen", "uploaded", name="contract_signature_method"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum("draft", "signed", "superseded", name="contract_status"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'signed', 'superseded')", name="ck_contracts_status"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["contract_template_version_id"], ["contract_template_versions.id"]),
        sa.ForeignKeyConstraint(["plan_version_id"], ["plan_versions.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contracts_student_status", "contracts", ["student_id", "status"], unique=False)


def downgrade() -> None:
    """Remove contracts and contract_template_versions, in FK-dependency order.

    MySQL repoints a FK's supporting index at a composite index sharing its
    leftmost column (dropping the auto-generated single-column one). Restore a
    plain index before dropping the composite one, or the FK is left
    unsupported (same fix as ``ea64c8751ff2``'s/``c7a3f9d21b6e``'s downgrades).
    """
    op.create_index("ix_contracts_student_id", "contracts", ["student_id"])
    op.drop_index("ix_contracts_student_status", table_name="contracts")
    op.drop_table("contracts")
    op.drop_table("contract_template_versions")
