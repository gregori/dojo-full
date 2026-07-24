"""Unit tests for merge-field validation and PDF rendering."""

import base64
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.services.contract_pdf_service import REQUIRED_STUDENT_FIELDS, ContractPdfService
from tests.unit.conftest import make_plan_tier, make_plan_version, make_student_with_contract_data


class TestValidateMergeFields:
    def test_passes_with_all_required_fields_populated(self, db_session):
        student = make_student_with_contract_data(db_session)

        ContractPdfService.validate_merge_fields(student)  # does not raise

    def test_fails_naming_a_single_missing_field(self, db_session):
        student = make_student_with_contract_data(db_session, phone=None)

        with pytest.raises(HTTPException) as exc_info:
            ContractPdfService.validate_merge_fields(student)

        assert exc_info.value.status_code == 400
        assert "phone" in exc_info.value.detail

    def test_fails_naming_every_missing_field(self, db_session):
        student = make_student_with_contract_data(db_session, phone=None, contract_cpf=None, birth_date=None)

        with pytest.raises(HTTPException) as exc_info:
            ContractPdfService.validate_merge_fields(student)

        assert "phone" in exc_info.value.detail
        assert "contract_cpf" in exc_info.value.detail
        assert "birth_date" in exc_info.value.detail

    def test_fails_when_all_fields_are_missing(self, db_session):
        student = make_student_with_contract_data(db_session, **{field: None for field in REQUIRED_STUDENT_FIELDS})

        with pytest.raises(HTTPException) as exc_info:
            ContractPdfService.validate_merge_fields(student)

        for field in REQUIRED_STUDENT_FIELDS:
            assert field in exc_info.value.detail


class TestRenderPdf:
    def _context(self, db_session):
        tier = make_plan_tier(db_session, weekly_frequency=3, name="3x por semana")
        version = make_plan_version(db_session, plan_tier_id=tier.id, price=Decimal("200.00"))
        student = make_student_with_contract_data(db_session)
        return ContractPdfService.build_context(student, tier, version)

    def test_produces_non_empty_pdf_bytes(self, db_session):
        context = self._context(db_session)

        content = ContractPdfService.render_pdf(
            "Contrato de {{ student.contract_name }}.\n\nPlano: {{ plan_tier.name }}.", context
        )

        assert content.startswith(b"%PDF-")
        assert len(content) > 0

    def test_signature_image_increases_output_size(self, db_session):
        context = self._context(db_session)
        png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        signature_png = base64.b64decode(png_b64)

        without_signature = ContractPdfService.render_pdf("Corpo do contrato.", context)
        with_signature = ContractPdfService.render_pdf("Corpo do contrato.", context, signature_png)

        assert with_signature.startswith(b"%PDF-")
        assert len(with_signature) > len(without_signature)
