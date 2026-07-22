"""Instructor/admin-only endpoints for the plan tier catalog and student plan assignment."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_instructor_or_admin
from app.schemas import PlanPriceUpdate, PlanTierCreate, PlanTierResponse, StudentPlanResponse
from app.services import PlanService, StudentPlanService, StudentService

router = APIRouter(prefix="/api/v1", tags=["plans"])


@router.get("/plans", response_model=list[PlanTierResponse])
def list_plan_tiers(db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)):
    """List plan tiers with each tier's current active price."""
    tiers = PlanService.get_tiers(db)
    return [
        PlanTierResponse(
            id=tier.id,
            weekly_frequency=tier.weekly_frequency,
            name=tier.name,
            is_active=tier.is_active,
            current_price=PlanService.get_current_price(db, tier.id),
        )
        for tier in tiers
    ]


@router.post("/plans", response_model=PlanTierResponse, status_code=status.HTTP_201_CREATED)
def create_plan_tier(
    data: PlanTierCreate, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """Create a new weekly-frequency plan tier with its initial price."""
    tier = PlanService.create_tier(db, data.weekly_frequency, data.name, data.price, created_by=current_user.id)
    return PlanTierResponse(
        id=tier.id,
        weekly_frequency=tier.weekly_frequency,
        name=tier.name,
        is_active=tier.is_active,
        current_price=data.price,
    )


@router.put("/plans/{tier_id}/price", response_model=PlanTierResponse)
def set_plan_tier_price(
    tier_id: str,
    data: PlanPriceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """Set a new price for a tier, creating a new version (does not reprice assigned students, D11)."""
    PlanService.set_price(db, tier_id, data.price, created_by=current_user.id)
    tier = PlanService.get_tier(db, tier_id)
    return PlanTierResponse(
        id=tier.id,
        weekly_frequency=tier.weekly_frequency,
        name=tier.name,
        is_active=tier.is_active,
        current_price=data.price,
    )


@router.post("/students/{student_id}/plan", response_model=StudentPlanResponse, status_code=status.HTTP_201_CREATED)
def assign_student_plan(
    student_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """Assign or reassign a student to the plan tier matching their declared weekly frequency (D1, D11)."""
    student = StudentService.get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return StudentPlanService.assign(db, student)


@router.get("/students/{student_id}/plan", response_model=list[StudentPlanResponse])
def get_student_plan_history(
    student_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """List a student's plan assignment history, most recent first."""
    return StudentPlanService.get_history(db, student_id)
