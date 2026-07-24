"""Instructor/admin-only endpoints for contract generation, signing, and download (D5: no public access)."""

import base64
import binascii
import mimetypes

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_instructor_or_admin
from app.models import Contract
from app.schemas import ContractResponse, ContractSignOnScreenRequest
from app.services import ContractService, StudentService

router = APIRouter(prefix="/api/v1", tags=["contracts"])


def _get_contract_or_404(db: Session, contract_id: str) -> Contract:
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    return contract


def _decode_signature_png(signature_png: str) -> bytes:
    """Decode a base64 PNG signature, tolerating a ``data:image/png;base64,`` URL prefix."""
    _, _, encoded = signature_png.partition(",") if signature_png.startswith("data:") else ("", "", signature_png)
    try:
        return base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature image data")


@router.post(
    "/students/{student_id}/contracts/matricular",
    response_model=ContractResponse,
    status_code=status.HTTP_201_CREATED,
)
def matricular_student(
    student_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """Assign/reassign the student's plan and generate the resulting contract draft (D1)."""
    student = StudentService.get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return ContractService.generate_for_matricula(db, student, current_user)


@router.get("/students/{student_id}/contracts", response_model=list[ContractResponse])
def list_student_contracts(
    student_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """List a student's contract history, most recent first."""
    return ContractService.get_history(db, student_id)


@router.get("/students/{student_id}/contracts/current", response_model=ContractResponse)
def get_current_student_contract(
    student_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """Return the student's current draft-or-signed contract."""
    contract = ContractService.get_active_or_draft(db, student_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No current contract for this student")
    return contract


@router.post("/contracts/{contract_id}/regenerate", response_model=ContractResponse)
def regenerate_contract_draft(
    contract_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """Re-render a draft's PDF in place, preserving its locked plan/template versions (D7)."""
    contract = _get_contract_or_404(db, contract_id)
    return ContractService.regenerate_draft(db, contract, current_user)


@router.post("/contracts/{contract_id}/sign/on-screen", response_model=ContractResponse)
def sign_contract_on_screen(
    contract_id: str,
    data: ContractSignOnScreenRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """Sign a draft with an in-app on-screen signature, embedded into the PDF."""
    contract = _get_contract_or_404(db, contract_id)
    signature_png = _decode_signature_png(data.signature_png)
    return ContractService.sign_on_screen(db, contract, signature_png, current_user)


@router.post("/contracts/{contract_id}/sign/upload", response_model=ContractResponse)
def sign_contract_by_upload(
    contract_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """Sign a draft by uploading an externally-signed/scanned PDF/JPEG/PNG (D4)."""
    contract = _get_contract_or_404(db, contract_id)
    return ContractService.sign_by_upload(db, contract, file, current_user)


@router.get("/contracts/{contract_id}/download")
def download_contract(
    contract_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """Stream the contract's current document bytes as an attachment (D5)."""
    contract = _get_contract_or_404(db, contract_id)
    if not contract.document_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract has no document")
    content, mime_type = ContractService.get_document_bytes(db, contract)
    extension = mimetypes.guess_extension(mime_type) or ""
    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="contract-{contract_id}{extension}"'},
    )
