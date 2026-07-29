"""Business rules for the plan tier catalog: CRUD and versioned pricing."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import PlanTier, PlanVersion


class PlanService:
    """Manage plan tiers and their versioned prices (D9: single global catalog, D10: no discounts)."""

    @staticmethod
    def get_tiers(db: Session) -> list[PlanTier]:
        """List all plan tiers, ordered by weekly frequency."""
        return db.query(PlanTier).order_by(PlanTier.weekly_frequency).all()

    @staticmethod
    def get_tier(db: Session, tier_id: str) -> PlanTier | None:
        return db.query(PlanTier).filter(PlanTier.id == tier_id).first()

    @staticmethod
    def get_active_version(db: Session, tier_id: str) -> PlanVersion | None:
        """Return a tier's current active priced version, if any."""
        return db.query(PlanVersion).filter(PlanVersion.plan_tier_id == tier_id, PlanVersion.status == "active").first()

    @staticmethod
    def get_current_price(db: Session, tier_id: str) -> Decimal | None:
        version = PlanService.get_active_version(db, tier_id)
        return version.price if version else None

    @staticmethod
    def create_tier(db: Session, weekly_frequency: int, name: str, price: Decimal, created_by: str) -> PlanTier:
        """Create a new plan tier with its initial active priced version."""
        existing = db.query(PlanTier).filter(PlanTier.weekly_frequency == weekly_frequency).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A plan tier for {weekly_frequency} classes/week already exists",
            )
        tier = PlanTier(weekly_frequency=weekly_frequency, name=name, is_active=True)
        db.add(tier)
        db.flush()
        version = PlanVersion(
            plan_tier_id=tier.id,
            price=price,
            status="active",
            effective_from=datetime.now(UTC),
            created_by=created_by,
        )
        db.add(version)
        db.commit()
        db.refresh(tier)
        return tier

    @staticmethod
    def set_price(db: Session, tier_id: str, price: Decimal, created_by: str) -> PlanVersion:
        """Create and activate a new priced version, superseding the previous one.

        Already-assigned students keep their locked ``PlanVersion`` (D11); this
        only affects future assignments.
        """
        tier = PlanService.get_tier(db, tier_id)
        if not tier:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan tier not found")

        previous = PlanService.get_active_version(db, tier_id)
        if previous:
            previous.status = "superseded"

        version = PlanVersion(
            plan_tier_id=tier_id,
            price=price,
            status="active",
            effective_from=datetime.now(UTC),
            created_by=created_by,
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version
