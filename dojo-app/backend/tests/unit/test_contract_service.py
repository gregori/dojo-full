"""Unit tests for the D1-D7 contract orchestration."""

import base64
import io
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.models import Contract, Document, StudentPlan
from app.services import ContractService, ContractTemplateService, PlanService
from tests.unit.conftest import (
    make_contract,
    make_contract_template_version,
    make_student_with_contract_data,
    make_user,
)

MINIMAL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def make_upload(
    content: bytes = b"%PDF-1.4 pdf-bytes",
    content_type: str = "application/pdf",
    filename: str = "signed.pdf",
):
    return UploadFile(file=io.BytesIO(content), filename=filename, headers=Headers({"content-type": content_type}))


@pytest.fixture(autouse=True)
def stub_document_upload(monkeypatch):
    """Avoid real object storage I/O; the storage key/content plumbing is tested elsewhere."""
    monkeypatch.setattr("app.services.contract_service.upload_document", lambda *a, **k: None)


class TestGenerateForMatricula:
    def _setup(self, db_session, weekly_frequency=2, price=Decimal("150.00")):
        instructor = make_user(db_session)
        PlanService.create_tier(
            db_session, weekly_frequency, f"{weekly_frequency}x por semana", price, created_by=instructor.id
        )
        ContractTemplateService.create_version(db_session, "Corpo do contrato.", datetime.now(UTC), instructor.id)
        student = make_student_with_contract_data(db_session, classes_per_week=weekly_frequency)
        return instructor, student

    def test_creates_draft_referencing_assigned_plan_and_active_template(self, db_session):
        instructor, student = self._setup(db_session)

        contract = ContractService.generate_for_matricula(db_session, student, instructor)

        assert contract.status == "draft"
        active_template = ContractTemplateService.get_active_version(db_session)
        assert contract.contract_template_version_id == active_template.id
        assert contract.document_id is not None

    def test_propagates_plan_tier_lookup_gap(self, db_session):
        instructor = make_user(db_session)
        ContractTemplateService.create_version(db_session, "Corpo", datetime.now(UTC), instructor.id)
        student = make_student_with_contract_data(db_session, classes_per_week=6)

        with pytest.raises(HTTPException) as exc_info:
            ContractService.generate_for_matricula(db_session, student, instructor)

        assert exc_info.value.status_code == 400

    def test_fails_with_named_fields_error_when_student_data_missing(self, db_session):
        instructor = make_user(db_session)
        PlanService.create_tier(db_session, 2, "2x por semana", Decimal("150.00"), created_by=instructor.id)
        ContractTemplateService.create_version(db_session, "Corpo", datetime.now(UTC), instructor.id)
        student = make_student_with_contract_data(db_session, classes_per_week=2, phone=None)

        with pytest.raises(HTTPException) as exc_info:
            ContractService.generate_for_matricula(db_session, student, instructor)

        assert exc_info.value.status_code == 400
        assert "phone" in exc_info.value.detail

    def test_no_plan_reassignment_committed_when_student_data_missing(self, db_session):
        """Regression (review finding 1): a 400 here must not leave a durable, orphaned StudentPlan."""
        instructor = make_user(db_session)
        PlanService.create_tier(db_session, 2, "2x por semana", Decimal("150.00"), created_by=instructor.id)
        ContractTemplateService.create_version(db_session, "Corpo", datetime.now(UTC), instructor.id)
        student = make_student_with_contract_data(db_session, classes_per_week=2, phone=None)

        with pytest.raises(HTTPException):
            ContractService.generate_for_matricula(db_session, student, instructor)

        assert db_session.query(StudentPlan).filter(StudentPlan.student_id == student.id).count() == 0

    def test_fails_when_no_active_contract_template_exists(self, db_session):
        instructor = make_user(db_session)
        PlanService.create_tier(db_session, 2, "2x por semana", Decimal("150.00"), created_by=instructor.id)
        student = make_student_with_contract_data(db_session, classes_per_week=2)

        with pytest.raises(HTTPException) as exc_info:
            ContractService.generate_for_matricula(db_session, student, instructor)

        assert exc_info.value.status_code == 400
        assert "template" in exc_info.value.detail.lower()

    def test_no_plan_reassignment_committed_when_no_active_template(self, db_session):
        """Regression (review finding 1): same guarantee for the missing-template failure mode."""
        instructor = make_user(db_session)
        PlanService.create_tier(db_session, 2, "2x por semana", Decimal("150.00"), created_by=instructor.id)
        student = make_student_with_contract_data(db_session, classes_per_week=2)

        with pytest.raises(HTTPException):
            ContractService.generate_for_matricula(db_session, student, instructor)

        assert db_session.query(StudentPlan).filter(StudentPlan.student_id == student.id).count() == 0

    def test_rerunning_against_existing_draft_updates_the_same_row(self, db_session):
        instructor, student = self._setup(db_session)
        first = ContractService.generate_for_matricula(db_session, student, instructor)
        first_document_id = first.document_id

        second = ContractService.generate_for_matricula(db_session, student, instructor)

        assert second.id == first.id
        assert db_session.query(Contract).filter(Contract.student_id == student.id).count() == 1
        assert second.document_id != first_document_id
        old_document = db_session.query(Document).filter(Document.id == first_document_id).first()
        assert old_document.status == "superseded"

    def test_rerunning_against_signed_contract_creates_new_draft_without_touching_signed_one(self, db_session):
        instructor, student = self._setup(db_session)
        first = ContractService.generate_for_matricula(db_session, student, instructor)
        signed = ContractService.sign_on_screen(db_session, first, MINIMAL_PNG, instructor)

        second = ContractService.generate_for_matricula(db_session, student, instructor)

        db_session.refresh(signed)
        assert second.id != signed.id
        assert second.status == "draft"
        assert signed.status == "signed"
        contracts = db_session.query(Contract).filter(Contract.student_id == student.id).all()
        assert len(contracts) == 2

    def test_third_call_during_renewal_reuses_the_draft_not_a_second_orphaned_one(self, db_session):
        """Regression (review finding 2): a signed+draft pair coexisting mid-renewal.

        A further "matricular" call must update the existing renewal draft in
        place, not create a second, orphaned draft alongside it.
        """
        instructor, student = self._setup(db_session)
        first = ContractService.generate_for_matricula(db_session, student, instructor)
        signed = ContractService.sign_on_screen(db_session, first, MINIMAL_PNG, instructor)
        renewal_draft = ContractService.generate_for_matricula(db_session, student, instructor)

        third = ContractService.generate_for_matricula(db_session, student, instructor)

        db_session.refresh(signed)
        assert third.id == renewal_draft.id
        assert signed.status == "signed"
        contracts = db_session.query(Contract).filter(Contract.student_id == student.id).all()
        assert len(contracts) == 2


class TestGetActiveOrDraft:
    def test_prefers_the_draft_when_a_signed_and_draft_contract_coexist(self, db_session):
        """Regression (review finding 2): mid-renewal, "current" must be the draft.

        Not the stale signed row the DB happens to return first.
        """
        instructor = make_user(db_session)
        student = make_student_with_contract_data(db_session)
        signed = make_contract(db_session, student_id=student.id, created_by=instructor.id, status="signed")
        draft = make_contract(db_session, student_id=student.id, created_by=instructor.id, status="draft")

        result = ContractService.get_active_or_draft(db_session, student.id)

        assert result.id == draft.id
        assert result.id != signed.id

    def test_falls_back_to_signed_when_no_draft_exists(self, db_session):
        instructor = make_user(db_session)
        student = make_student_with_contract_data(db_session)
        signed = make_contract(db_session, student_id=student.id, created_by=instructor.id, status="signed")

        result = ContractService.get_active_or_draft(db_session, student.id)

        assert result.id == signed.id

    def test_returns_none_when_no_draft_or_signed_contract_exists(self, db_session):
        student = make_student_with_contract_data(db_session)

        assert ContractService.get_active_or_draft(db_session, student.id) is None


class TestRegenerateDraft:
    def test_preserves_plan_version_and_template_version_even_if_catalog_changed(self, db_session):
        instructor = make_user(db_session)
        student = make_student_with_contract_data(db_session)
        contract = make_contract(db_session, student_id=student.id, created_by=instructor.id)
        original_plan_version_id = contract.plan_version_id
        original_template_version_id = contract.contract_template_version_id

        regenerated = ContractService.regenerate_draft(db_session, contract, instructor)

        assert regenerated.plan_version_id == original_plan_version_id
        assert regenerated.contract_template_version_id == original_template_version_id

    def test_rejects_regeneration_of_a_signed_contract(self, db_session):
        instructor = make_user(db_session)
        student = make_student_with_contract_data(db_session)
        contract = make_contract(db_session, student_id=student.id, created_by=instructor.id, status="signed")

        with pytest.raises(HTTPException) as exc_info:
            ContractService.regenerate_draft(db_session, contract, instructor)

        assert exc_info.value.status_code == 409


class TestSignOnScreen:
    def test_sets_signature_method_status_and_signed_at(self, db_session):
        instructor = make_user(db_session)
        student = make_student_with_contract_data(db_session)
        contract = make_contract(db_session, student_id=student.id, created_by=instructor.id)

        signed = ContractService.sign_on_screen(db_session, contract, MINIMAL_PNG, instructor)

        assert signed.signature_method == "on_screen"
        assert signed.status == "signed"
        assert signed.signed_at is not None

    def test_supersedes_a_prior_signed_contract_for_the_same_student(self, db_session):
        instructor = make_user(db_session)
        student = make_student_with_contract_data(db_session)
        first_draft = make_contract(db_session, student_id=student.id, created_by=instructor.id)
        first_signed = ContractService.sign_on_screen(db_session, first_draft, MINIMAL_PNG, instructor)
        second_draft = make_contract(
            db_session,
            student_id=student.id,
            created_by=instructor.id,
            contract_template_version_id=first_draft.contract_template_version_id,
            plan_version_id=first_draft.plan_version_id,
        )

        ContractService.sign_on_screen(db_session, second_draft, MINIMAL_PNG, instructor)

        db_session.refresh(first_signed)
        assert first_signed.status == "superseded"

    def test_rejects_signing_a_non_draft_contract(self, db_session):
        instructor = make_user(db_session)
        student = make_student_with_contract_data(db_session)
        contract = make_contract(db_session, student_id=student.id, created_by=instructor.id, status="signed")

        with pytest.raises(HTTPException) as exc_info:
            ContractService.sign_on_screen(db_session, contract, MINIMAL_PNG, instructor)

        assert exc_info.value.status_code == 409


class TestSignByUpload:
    def test_sets_signature_method_status_and_signed_at(self, db_session):
        instructor = make_user(db_session)
        student = make_student_with_contract_data(db_session)
        contract = make_contract(db_session, student_id=student.id, created_by=instructor.id)

        signed = ContractService.sign_by_upload(db_session, contract, make_upload(), instructor)

        assert signed.signature_method == "uploaded"
        assert signed.status == "signed"
        assert signed.signed_at is not None

    def test_rejects_disallowed_mime_type(self, db_session):
        instructor = make_user(db_session)
        student = make_student_with_contract_data(db_session)
        contract = make_contract(db_session, student_id=student.id, created_by=instructor.id)

        with pytest.raises(HTTPException) as exc_info:
            ContractService.sign_by_upload(
                db_session, contract, make_upload(content_type="text/plain", filename="x.txt"), instructor
            )

        assert exc_info.value.status_code == 400

    def test_rejects_oversized_file(self, db_session):
        instructor = make_user(db_session)
        student = make_student_with_contract_data(db_session)
        contract = make_contract(db_session, student_id=student.id, created_by=instructor.id)
        oversized = b"0" * (10 * 1024 * 1024 + 1)

        with pytest.raises(HTTPException) as exc_info:
            ContractService.sign_by_upload(db_session, contract, make_upload(content=oversized), instructor)

        assert exc_info.value.status_code == 400

    def test_rejects_signing_a_non_draft_contract(self, db_session):
        instructor = make_user(db_session)
        student = make_student_with_contract_data(db_session)
        contract = make_contract(db_session, student_id=student.id, created_by=instructor.id, status="superseded")

        with pytest.raises(HTTPException) as exc_info:
            ContractService.sign_by_upload(db_session, contract, make_upload(), instructor)

        assert exc_info.value.status_code == 409
