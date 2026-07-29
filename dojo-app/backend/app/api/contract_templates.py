"""Instructor/admin-only endpoints for authoring the versioned legal contract template (D2)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_instructor_or_admin
from app.schemas import ContractTemplateVersionCreate, ContractTemplateVersionResponse
from app.services import ContractTemplateService

router = APIRouter(prefix="/api/v1/contract-templates", tags=["contract-templates"])


@router.get("", response_model=list[ContractTemplateVersionResponse])
def list_contract_template_versions(
    db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """List the template version history, most recent first."""
    return ContractTemplateService.get_history(db)


@router.get("/active", response_model=ContractTemplateVersionResponse)
def get_active_contract_template_version(
    db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """Return the currently active template version."""
    version = ContractTemplateService.get_active_version(db)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active contract template exists")
    return version


@router.post("", response_model=ContractTemplateVersionResponse, status_code=status.HTTP_201_CREATED)
def create_contract_template_version(
    data: ContractTemplateVersionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """Author a new template version, superseding the previous active one."""
    return ContractTemplateService.create_version(db, data.body, data.effective_from, created_by=current_user.id)
