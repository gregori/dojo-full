"""The D1-D7 contract orchestration: matricula/renewal, draft regeneration, and signing."""

import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.storage import download_document, upload_document
from app.core.uploads import read_bounded, validate_file
from app.models import Contract, Document, Student, User
from app.services.contract_pdf_service import ContractPdfService
from app.services.contract_template_service import ContractTemplateService
from app.services.student_plan_service import StudentPlanService


class ContractService:
    """Generate, regenerate, and sign a student's contract (CON-01-CON-04)."""

    @staticmethod
    def get_active_or_draft(db: Session, student_id: str) -> Contract | None:
        """Return the student's current draft-or-signed contract, if any.

        A ``draft`` and a ``signed`` contract can legitimately coexist mid-renewal
        (D6: the previous ``signed`` row isn't superseded until the new one is
        itself signed), so this must deterministically prefer the ``draft`` --
        it's the one still awaiting action -- rather than whichever row the
        database happens to return first.
        """
        draft = db.query(Contract).filter(Contract.student_id == student_id, Contract.status == "draft").first()
        if draft:
            return draft
        return db.query(Contract).filter(Contract.student_id == student_id, Contract.status == "signed").first()

    @staticmethod
    def get_history(db: Session, student_id: str) -> list[Contract]:
        """Return a student's full contract history, most recent first."""
        return db.query(Contract).filter(Contract.student_id == student_id).order_by(Contract.created_at.desc()).all()

    @staticmethod
    def _render_and_store_document(
        db: Session,
        student: Student,
        template_body: str,
        context: dict,
        signature_png: bytes | None,
        uploaded_by_user_id: str,
    ) -> Document:
        """Render a contract PDF and persist it as a new active ``Document`` (not yet committed)."""
        content = ContractPdfService.render_pdf(template_body, context, signature_png)
        storage_key = f"contracts/{student.id}/{uuid.uuid4()}.pdf"
        upload_document(storage_key, content, "application/pdf")
        document = Document(
            student_id=student.id,
            document_type="contract",
            storage_key=storage_key,
            mime_type="application/pdf",
            size_bytes=len(content),
            uploaded_by_user_id=uploaded_by_user_id,
            uploaded_by_student_self=False,
            status="active",
        )
        db.add(document)
        db.flush()
        return document

    @staticmethod
    def _supersede_document(document: Document | None, actor: str) -> None:
        """Mark a contract's previous document superseded rather than mutating it in place (D7a)."""
        if document is None:
            return
        document.status = "superseded"
        document.deleted_at = datetime.now(UTC)
        document.deleted_by = actor

    @staticmethod
    def generate_for_matricula(db: Session, student: Student, current_user: User) -> Contract:
        """Assign/reassign the student's plan and generate the resulting contract draft (D1).

        Reuses an existing ``draft`` in place (repricing, since this is the
        explicit re-run D7b carves out), creates a new ``draft`` alongside an
        existing ``signed`` contract (renewal, D6), or creates the first one.
        """
        # Validated before StudentPlanService.assign (which commits internally, so
        # a failure here must not leave a plan reassignment durably committed with
        # no matching contract -- neither check depends on the assignment's result).
        ContractPdfService.validate_merge_fields(student)
        template_version = ContractTemplateService.get_active_version(db)
        if template_version is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active contract template exists")

        student_id = student.id  # Capture student.id before StudentPlanService.assign() commits
        student_plan = StudentPlanService.assign(db, student)
        # After StudentPlanService.assign()'s internal commit, query a fresh student object
        # to avoid ORM state issues with the now-detached student object
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found after assignment")
        plan_version = student_plan.plan_version
        context = ContractPdfService.build_context(student, plan_version.plan_tier, plan_version)
        document = ContractService._render_and_store_document(
            db, student, template_version.body, context, None, current_user.id
        )

        existing = ContractService.get_active_or_draft(db, student.id)
        if existing and existing.status == "draft":
            ContractService._supersede_document(existing.document, current_user.id)
            existing.document_id = document.id
            existing.contract_template_version_id = template_version.id
            existing.plan_version_id = plan_version.id
            contract = existing
        else:
            contract = Contract(
                student_id=student.id,
                contract_template_version_id=template_version.id,
                plan_version_id=plan_version.id,
                document_id=document.id,
                status="draft",
                created_by=current_user.id,
            )
            db.add(contract)

        db.commit()
        db.refresh(contract)
        return contract

    @staticmethod
    def _require_draft(contract: Contract) -> None:
        if contract.status != "draft":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Contract is not a draft")

    @staticmethod
    def regenerate_draft(db: Session, contract: Contract, current_user: User) -> Contract:
        """Re-render a draft's PDF from its unchanged plan/template versions (D7).

        Preserves ``plan_version_id``/``contract_template_version_id`` even if
        the catalog or template have since changed (D7b) -- only the
        student's current data is re-read.
        """
        ContractService._require_draft(contract)
        ContractPdfService.validate_merge_fields(contract.student)

        plan_version = contract.plan_version
        context = ContractPdfService.build_context(contract.student, plan_version.plan_tier, plan_version)
        document = ContractService._render_and_store_document(
            db, contract.student, contract.contract_template_version.body, context, None, current_user.id
        )

        ContractService._supersede_document(contract.document, current_user.id)
        contract.document_id = document.id

        db.commit()
        db.refresh(contract)
        return contract

    @staticmethod
    def _supersede_other_signed_contracts(db: Session, student_id: str, keep_contract_id: str) -> None:
        """Supersede any other ``signed`` contract for this student at the signing moment (D6)."""
        others = (
            db.query(Contract)
            .filter(Contract.student_id == student_id, Contract.status == "signed", Contract.id != keep_contract_id)
            .all()
        )
        for other in others:
            other.status = "superseded"

    @staticmethod
    def sign_on_screen(db: Session, contract: Contract, signature_png: bytes, current_user: User) -> Contract:
        """Sign a draft with an in-app on-screen signature, embedding it into the PDF (D6, D7a)."""
        ContractService._require_draft(contract)

        plan_version = contract.plan_version
        context = ContractPdfService.build_context(contract.student, plan_version.plan_tier, plan_version)
        document = ContractService._render_and_store_document(
            db, contract.student, contract.contract_template_version.body, context, signature_png, current_user.id
        )

        ContractService._supersede_document(contract.document, current_user.id)
        contract.document_id = document.id
        contract.signature_method = "on_screen"
        contract.status = "signed"
        contract.signed_at = datetime.now(UTC)
        ContractService._supersede_other_signed_contracts(db, contract.student_id, contract.id)

        db.commit()
        db.refresh(contract)
        return contract

    @staticmethod
    def sign_by_upload(db: Session, contract: Contract, file: UploadFile, current_user: User) -> Contract:
        """Sign a draft by uploading an externally-signed/scanned PDF/JPEG/PNG (D3, D4)."""
        ContractService._require_draft(contract)

        content = read_bounded(file)
        validate_file(file, content)
        extension = Path(file.filename or "").suffix
        storage_key = f"contracts/{contract.student_id}/{uuid.uuid4()}{extension}"
        upload_document(storage_key, content, file.content_type)
        document = Document(
            student_id=contract.student_id,
            document_type="contract",
            storage_key=storage_key,
            mime_type=file.content_type,
            size_bytes=len(content),
            uploaded_by_user_id=current_user.id,
            uploaded_by_student_self=False,
            status="active",
        )
        db.add(document)
        db.flush()

        ContractService._supersede_document(contract.document, current_user.id)
        contract.document_id = document.id
        contract.signature_method = "uploaded"
        contract.status = "signed"
        contract.signed_at = datetime.now(UTC)
        ContractService._supersede_other_signed_contracts(db, contract.student_id, contract.id)

        db.commit()
        db.refresh(contract)
        return contract

    @staticmethod
    def get_document_bytes(db: Session, contract: Contract) -> tuple[bytes, str]:
        """Return a contract's current document bytes and MIME type, for the download endpoint (D5)."""
        content = download_document(contract.document.storage_key)
        return content, contract.document.mime_type
