"""Unit tests for medical exam status computation, supersession, and validation."""

import io
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.core.security import get_password_hash
from app.models import Document, MedicalExam
from app.services import MedicalExamService
from tests.unit.conftest import make_student, make_user


def make_upload(
    content: bytes = b"%PDF-1.4 pdf-bytes",
    content_type: str = "application/pdf",
    filename: str = "exam.pdf",
):
    """Build a minimal in-memory UploadFile for service-layer tests."""
    return UploadFile(file=io.BytesIO(content), filename=filename, headers=Headers({"content-type": content_type}))


class _CountingStream:
    """A file-like object that reports how many bytes were served, without pre-materializing them."""

    def __init__(self, total_size: int):
        self._remaining = total_size
        self.bytes_served = 0

    def read(self, size: int = -1) -> bytes:
        if self._remaining <= 0:
            return b""
        chunk_size = size if size and size >= 0 else self._remaining
        served = min(chunk_size, self._remaining)
        self._remaining -= served
        self.bytes_served += served
        return b"0" * served


class TestComputeStatus:
    def test_no_active_record_is_sem_registro(self):
        assert MedicalExamService.compute_status(None) == "sem_registro"

    def test_far_from_expiry_is_valido(self):
        expires_at = datetime.now(UTC) + timedelta(days=200)
        assert MedicalExamService.compute_status(expires_at) == "valido"

    def test_within_thirty_days_is_vencendo(self):
        expires_at = datetime.now(UTC) + timedelta(days=15)
        assert MedicalExamService.compute_status(expires_at) == "vencendo"

    def test_past_expiry_is_vencido(self):
        expires_at = datetime.now(UTC) - timedelta(days=1)
        assert MedicalExamService.compute_status(expires_at) == "vencido"

    def test_naive_datetime_from_sqlite_is_treated_as_utc(self):
        # SQLite round-trips DateTime(timezone=True) columns without tzinfo;
        # the comparison must not raise and must still classify correctly.
        naive_expires_at = (datetime.now(UTC) - timedelta(days=1)).replace(tzinfo=None)
        assert MedicalExamService.compute_status(naive_expires_at) == "vencido"


class TestRecordExam:
    def test_record_without_file_creates_active_record_with_no_document(self, db_session):
        student = make_student(db_session)
        instructor = make_user(db_session)

        record = MedicalExamService.record_exam(
            db_session,
            student,
            datetime.now(UTC).date(),
            None,
            uploaded_by_user_id=instructor.id,
            uploaded_by_student_self=False,
        )

        assert record.status == "active"
        assert record.document_id is None
        assert db_session.query(MedicalExam).filter(MedicalExam.student_id == student.id).count() == 1

    def test_record_with_file_uploads_and_persists_document(self, db_session, monkeypatch):
        uploaded = {}
        monkeypatch.setattr(
            "app.services.medical_exam_service.upload_document",
            lambda key, content, content_type: uploaded.update(key=key, content=content, content_type=content_type),
        )
        student = make_student(db_session)
        instructor = make_user(db_session)

        record = MedicalExamService.record_exam(
            db_session,
            student,
            datetime.now(UTC).date(),
            make_upload(),
            uploaded_by_user_id=instructor.id,
            uploaded_by_student_self=False,
        )

        assert record.document is not None
        assert record.document.status == "active"
        assert record.document.uploaded_by_user_id == instructor.id
        assert record.document.uploaded_by_student_self is False
        assert uploaded["key"] == record.document.storage_key
        assert uploaded["content"] == b"%PDF-1.4 pdf-bytes"

    def test_new_submission_supersedes_prior_active_record(self, db_session, monkeypatch):
        monkeypatch.setattr("app.services.medical_exam_service.upload_document", lambda *a, **k: None)
        student = make_student(db_session)
        first_instructor = make_user(db_session)
        second_instructor = make_user(db_session)

        first = MedicalExamService.record_exam(
            db_session,
            student,
            datetime.now(UTC).date(),
            make_upload(),
            uploaded_by_user_id=first_instructor.id,
            uploaded_by_student_self=False,
        )
        second = MedicalExamService.record_exam(
            db_session,
            student,
            datetime.now(UTC).date(),
            make_upload(),
            uploaded_by_user_id=second_instructor.id,
            uploaded_by_student_self=False,
        )

        db_session.refresh(first)
        active_records = (
            db_session.query(MedicalExam)
            .filter(MedicalExam.student_id == student.id, MedicalExam.status == "active")
            .all()
        )
        assert first.status == "superseded"
        assert first.document.status == "superseded"
        assert first.document.deleted_at is not None
        assert first.document.deleted_by == second_instructor.id
        assert len(active_records) == 1
        assert active_records[0].id == second.id
        assert db_session.query(MedicalExam).filter(MedicalExam.student_id == student.id).count() == 2

    def test_student_self_service_supersession_records_student_actor(self, db_session, monkeypatch):
        monkeypatch.setattr("app.services.medical_exam_service.upload_document", lambda *a, **k: None)
        student = make_student(db_session)

        first = MedicalExamService.record_exam(
            db_session,
            student,
            datetime.now(UTC).date(),
            make_upload(),
            uploaded_by_user_id=None,
            uploaded_by_student_self=True,
        )
        MedicalExamService.record_exam(
            db_session,
            student,
            datetime.now(UTC).date(),
            make_upload(),
            uploaded_by_user_id=None,
            uploaded_by_student_self=True,
        )

        db_session.refresh(first)
        assert first.document.deleted_by == f"student:{student.id}"

    def test_rejects_disallowed_mime_type(self, db_session):
        student = make_student(db_session)
        instructor = make_user(db_session)

        with pytest.raises(HTTPException) as exc_info:
            MedicalExamService.record_exam(
                db_session,
                student,
                datetime.now(UTC).date(),
                make_upload(content_type="text/plain", filename="exam.txt"),
                uploaded_by_user_id=instructor.id,
                uploaded_by_student_self=False,
            )

        assert exc_info.value.status_code == 400

    def test_rejects_oversized_file(self, db_session):
        student = make_student(db_session)
        instructor = make_user(db_session)
        oversized = b"0" * (10 * 1024 * 1024 + 1)

        with pytest.raises(HTTPException) as exc_info:
            MedicalExamService.record_exam(
                db_session,
                student,
                datetime.now(UTC).date(),
                make_upload(content=oversized),
                uploaded_by_user_id=instructor.id,
                uploaded_by_student_self=False,
            )

        assert exc_info.value.status_code == 400
        assert db_session.query(Document).count() == 0

    def test_rejects_spoofed_content_type_with_mismatched_magic_bytes(self, db_session):
        student = make_student(db_session)
        instructor = make_user(db_session)

        with pytest.raises(HTTPException) as exc_info:
            MedicalExamService.record_exam(
                db_session,
                student,
                datetime.now(UTC).date(),
                make_upload(
                    content=b"<html><script>evil()</script></html>",
                    content_type="image/png",
                    filename="evil.html",
                ),
                uploaded_by_user_id=instructor.id,
                uploaded_by_student_self=False,
            )

        assert exc_info.value.status_code == 400
        assert db_session.query(Document).count() == 0

    def test_oversized_upload_is_rejected_without_reading_the_entire_stream(self, db_session):
        student = make_student(db_session)
        instructor = make_user(db_session)
        declared_size = 100 * 1024 * 1024  # far beyond the 10MB limit
        stream = _CountingStream(declared_size)
        upload = UploadFile(file=stream, filename="huge.pdf", headers=Headers({"content-type": "application/pdf"}))

        with pytest.raises(HTTPException) as exc_info:
            MedicalExamService.record_exam(
                db_session,
                student,
                datetime.now(UTC).date(),
                upload,
                uploaded_by_user_id=instructor.id,
                uploaded_by_student_self=False,
            )

        assert exc_info.value.status_code == 400
        assert db_session.query(Document).count() == 0
        # The bounded reader must stop well before the full declared size is served.
        assert stream.bytes_served <= 11 * 1024 * 1024


class TestAuthenticateStudent:
    def test_valid_credentials_return_student(self, db_session):
        student = make_student(db_session, pin=get_password_hash("1234"))

        result = MedicalExamService.authenticate_student(db_session, student.registration_number, "1234")

        assert result is not None
        assert result.id == student.id

    def test_wrong_pin_returns_none(self, db_session):
        student = make_student(db_session, pin=get_password_hash("1234"))

        assert MedicalExamService.authenticate_student(db_session, student.registration_number, "0000") is None

    def test_inactive_student_returns_none(self, db_session):
        student = make_student(db_session, pin=get_password_hash("1234"), is_active=False)

        assert MedicalExamService.authenticate_student(db_session, student.registration_number, "1234") is None


class TestDashboard:
    def test_dashboard_includes_only_vencendo_and_vencido_active_students(self, db_session, monkeypatch):
        monkeypatch.setattr("app.services.medical_exam_service.upload_document", lambda *a, **k: None)
        instructor = make_user(db_session)

        valido_student = make_student(db_session)
        vencendo_student = make_student(db_session)
        vencido_student = make_student(db_session)
        sem_registro_student = make_student(db_session)
        inactive_vencido_student = make_student(db_session, is_active=False)

        MedicalExamService.record_exam(
            db_session,
            valido_student,
            (datetime.now(UTC) - timedelta(days=10)).date(),
            None,
            uploaded_by_user_id=instructor.id,
            uploaded_by_student_self=False,
        )
        MedicalExamService.record_exam(
            db_session,
            vencendo_student,
            (datetime.now(UTC) - timedelta(days=350)).date(),
            None,
            uploaded_by_user_id=instructor.id,
            uploaded_by_student_self=False,
        )
        MedicalExamService.record_exam(
            db_session,
            vencido_student,
            (datetime.now(UTC) - timedelta(days=400)).date(),
            None,
            uploaded_by_user_id=instructor.id,
            uploaded_by_student_self=False,
        )
        MedicalExamService.record_exam(
            db_session,
            inactive_vencido_student,
            (datetime.now(UTC) - timedelta(days=400)).date(),
            None,
            uploaded_by_user_id=instructor.id,
            uploaded_by_student_self=False,
        )

        dashboard = MedicalExamService.get_dashboard(db_session)
        dashboard_student_ids = {item["student_id"] for item in dashboard}

        assert dashboard_student_ids == {vencendo_student.id, vencido_student.id}
        assert valido_student.id not in dashboard_student_ids
        assert sem_registro_student.id not in dashboard_student_ids
        assert inactive_vencido_student.id not in dashboard_student_ids
