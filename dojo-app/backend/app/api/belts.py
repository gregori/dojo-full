from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import (
    get_current_admin,
    get_current_instructor_or_admin,
)
from app.schemas import (
    BeltCreate,
    BeltRequirementCreate,
    BeltRequirementResponse,
    BeltRequirementUpdate,
    BeltResponse,
    BeltUpdate,
    BeltWithRequirements,
)
from app.services import BeltService

router = APIRouter(prefix="/api/v1/belts", tags=["belts"])


@router.get("", response_model=list[BeltResponse])
def list_belts(
    category: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """List all belts."""
    return BeltService.get_belts(db, category=category, skip=skip, limit=limit)


@router.get("/{belt_id}", response_model=BeltWithRequirements)
def get_belt(belt_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)):
    """Get belt by ID with requirements."""
    return BeltService.get_belt(db, belt_id)


@router.post("", response_model=BeltResponse, status_code=status.HTTP_201_CREATED)
def create_belt(belt_data: BeltCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    """Create a new belt (admin only)."""
    return BeltService.create_belt(db, belt_data)


@router.put("/{belt_id}", response_model=BeltResponse)
def update_belt(
    belt_id: str, belt_data: BeltUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)
):
    """Update belt (admin only)."""
    return BeltService.update_belt(db, belt_id, belt_data)


@router.delete("/{belt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_belt(belt_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    """Delete belt (admin only)."""
    BeltService.delete_belt(db, belt_id)


# Belt Requirements
@router.post("/{belt_id}/requirements", response_model=BeltRequirementResponse, status_code=status.HTTP_201_CREATED)
def add_requirement(
    belt_id: str,
    req_data: BeltRequirementCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Add requirement to belt (admin only)."""
    req_data.belt_id = belt_id
    return BeltService.create_requirement(db, req_data)


@router.get("/{belt_id}/requirements", response_model=list[BeltRequirementResponse])
def list_requirements(
    belt_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """List requirements for a belt."""
    return BeltService.get_requirements_by_belt(db, belt_id)


@router.delete("/requirements/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_requirement(requirement_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    """Delete a requirement (admin only)."""
    BeltService.delete_requirement(db, requirement_id)


@router.put("/requirements/{requirement_id}", response_model=BeltRequirementResponse)
def update_requirement(
    requirement_id: str,
    req_data: BeltRequirementUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Update a requirement (admin only)."""
    return BeltService.update_requirement(db, requirement_id, req_data)
