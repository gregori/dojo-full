"""Business rules for medical exam records: status computation, supersession, and public self-service."""

import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.core.storage import upload_document
from app.models import Document, MedicalExam, Student
from app.services.student_service import StudentService

EXAM_VALIDITY = timedelta(days=365)
EXPIRY_WARNING_WINDOW = timedelta(days=30)
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
UPLOAD_CHUNK_SIZE = 1024 * 1024

# Magic-byte signatures for the allowed MIME types, so validation checks actual
# file content rather than the client-supplied (and fully spoofable) Content-Type header.
MIME_SIGNATURES: dict[str, bytes] = {
    "application/pdf": b"%PDF-",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8\xff",
}


class MedicalExamService:
    """Record medical exams, compute status, and manage the append-only history."""

    @staticmethod
    def authenticate_student(db: Session, registration_number: str, pin: str) -> Student | None:
        """Return the active student for valid public credentials, otherwise ``None``."""
        student = StudentService.get_student_by_registration(db, registration_number)
        if not student or not student.is_active or not verify_password(pin, student.pin):
            return None
        return student

    @staticmethod
    def _read_bounded(file: UploadFile) -> bytes:
        """Read the upload in chunks, rejecting early once it exceeds the size limit.

        Avoids buffering an unbounded request body into memory before the size
        check runs, since the endpoint is reachable without full authentication.
        """
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = file.file.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_FILE_SIZE_BYTES:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds the 10MB limit")
            chunks.append(chunk)
        return b"".join(chunks)

    @staticmethod
    def _validate_file(file: UploadFile, content: bytes) -> None:
        signature = MIME_SIGNATURES.get(file.content_type or "")
        if signature is None or not content.startswith(signature):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF, JPEG, or PNG files are accepted"
            )

    @staticmethod
    def _get_active_record(db: Session, student_id: str, *, for_update: bool = False) -> MedicalExam | None:
        query = db.query(MedicalExam).filter(MedicalExam.student_id == student_id, MedicalExam.status == "active")
        if for_update:
            query = query.with_for_update()
        return query.first()

    @staticmethod
    def compute_status(expires_at: datetime | None) -> str:
        """Compute valido/vencendo/vencido/sem_registro from an active record's expiry."""
        if expires_at is None:
            return "sem_registro"
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        if now >= expires_at:
            return "vencido"
        if now >= expires_at - EXPIRY_WARNING_WINDOW:
            return "vencendo"
        return "valido"

    @staticmethod
    def get_status(db: Session, student_id: str) -> dict:
        """Return the computed status for a student, along with the active record's dates, if any."""
        record = MedicalExamService._get_active_record(db, student_id)
        return {
            "student_id": student_id,
            "status": MedicalExamService.compute_status(record.expires_at if record else None),
            "exam_date": record.exam_date if record else None,
            "expires_at": record.expires_at if record else None,
        }

    @staticmethod
    def get_history(db: Session, student_id: str) -> list[MedicalExam]:
        """Return a student's full medical exam history, most recent first."""
        return (
            db.query(MedicalExam)
            .filter(MedicalExam.student_id == student_id)
            .order_by(MedicalExam.exam_date.desc(), MedicalExam.created_at.desc())
            .all()
        )

    @staticmethod
    def record_exam(
        db: Session,
        student: Student,
        exam_date: date,
        file: UploadFile | None,
        *,
        uploaded_by_user_id: str | None,
        uploaded_by_student_self: bool,
    ) -> MedicalExam:
        """Record a new exam for a student, superseding the prior active record, if any."""
        actor = uploaded_by_user_id or (f"student:{student.id}" if uploaded_by_student_self else None)

        document = None
        if file is not None:
            content = MedicalExamService._read_bounded(file)
            MedicalExamService._validate_file(file, content)
            extension = Path(file.filename or "").suffix
            storage_key = f"medical-exams/{student.id}/{uuid.uuid4()}{extension}"
            upload_document(storage_key, content, file.content_type)
            document = Document(
                student_id=student.id,
                document_type="medical_exam",
                storage_key=storage_key,
                mime_type=file.content_type,
                size_bytes=len(content),
                uploaded_by_user_id=uploaded_by_user_id,
                uploaded_by_student_self=uploaded_by_student_self,
                status="active",
            )
            db.add(document)
            db.flush()

        previous = MedicalExamService._get_active_record(db, student.id, for_update=True)
        if previous:
            previous.status = "superseded"
            if previous.document:
                previous.document.status = "superseded"
                previous.document.deleted_at = datetime.now(UTC)
                previous.document.deleted_by = actor

        exam_datetime = datetime.combine(exam_date, datetime.min.time(), tzinfo=UTC)
        record = MedicalExam(
            student_id=student.id,
            exam_date=exam_datetime,
            expires_at=exam_datetime + EXAM_VALIDITY,
            document_id=document.id if document else None,
            status="active",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_dashboard(db: Session) -> list[dict]:
        """Return active students whose current medical-exam status is vencendo or vencido."""
        results = []
        students = db.query(Student).filter(Student.is_active.is_(True)).all()
        for student in students:
            record = MedicalExamService._get_active_record(db, student.id)
            computed = MedicalExamService.compute_status(record.expires_at if record else None)
            if computed in ("vencendo", "vencido"):
                results.append(
                    {
                        "student_id": student.id,
                        "student_name": student.full_name,
                        "registration_number": student.registration_number,
                        "status": computed,
                        "exam_date": record.exam_date if record else None,
                        "expires_at": record.expires_at if record else None,
                    }
                )
        return results
