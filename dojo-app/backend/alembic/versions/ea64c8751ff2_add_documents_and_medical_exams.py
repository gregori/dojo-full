"""Add documents and medical_exams.

Revision ID: ea64c8751ff2
Revises: b39e1a4c7d20
Create Date: 2026-07-19
"""

import sqlalchemy as sa

from alembic import op

revision = "ea64c8751ff2"
down_revision = "b39e1a4c7d20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the generic documents table and the medical_exams history table."""
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("uploaded_by_student_self", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "status",
            sa.Enum("active", "superseded", "deleted", name="document_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'superseded', 'deleted')", name="ck_documents_status"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_documents_storage_key"),
    )
    op.create_index("ix_documents_student_type", "documents", ["student_id", "document_type"], unique=False)

    op.create_table(
        "medical_exams",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("exam_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "superseded", name="medical_exam_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'superseded')", name="ck_medical_exams_status"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_medical_exams_student_status", "medical_exams", ["student_id", "status"], unique=False)


def downgrade() -> None:
    """Remove medical_exams and documents.

    MySQL may repoint a foreign key's supporting index at a composite index
    that shares its leftmost column (dropping the auto-generated single-column
    one). Restore a plain index on the FK column before dropping the
    composite index, or the FK is left unsupported (same fix as
    ``b39e1a4c7d20``'s ``attendances`` downgrade).
    """
    op.create_index("ix_medical_exams_student_id", "medical_exams", ["student_id"])
    op.drop_index("ix_medical_exams_student_status", table_name="medical_exams")
    op.drop_table("medical_exams")
    op.create_index("ix_documents_student_id", "documents", ["student_id"])
    op.drop_index("ix_documents_student_type", table_name="documents")
    op.drop_table("documents")
