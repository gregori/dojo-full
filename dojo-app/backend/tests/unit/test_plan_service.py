"""Unit tests for the plan tier catalog: creation, versioned pricing, and supersession."""

from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models import PlanVersion
from app.services import PlanService
from tests.unit.conftest import make_plan_tier, make_user


class TestCreateTier:
    def test_creates_tier_with_active_version(self, db_session):
        user = make_user(db_session)

        tier = PlanService.create_tier(db_session, 2, "2x por semana", Decimal("150.00"), created_by=user.id)

        assert tier.weekly_frequency == 2
        assert tier.is_active is True
        version = PlanService.get_active_version(db_session, tier.id)
        assert version.price == Decimal("150.00")
        assert version.status == "active"

    def test_duplicate_weekly_frequency_is_rejected(self, db_session):
        user = make_user(db_session)
        PlanService.create_tier(db_session, 3, "3x por semana", Decimal("180.00"), created_by=user.id)

        with pytest.raises(HTTPException) as exc_info:
            PlanService.create_tier(db_session, 3, "3x por semana (dup)", Decimal("200.00"), created_by=user.id)

        assert exc_info.value.status_code == 409


class TestSetPrice:
    def test_new_price_supersedes_previous_version(self, db_session):
        user = make_user(db_session)
        tier = make_plan_tier(db_session)
        first_version = PlanService.set_price(db_session, tier.id, Decimal("100.00"), created_by=user.id)

        second_version = PlanService.set_price(db_session, tier.id, Decimal("120.00"), created_by=user.id)

        db_session.refresh(first_version)
        assert first_version.status == "superseded"
        assert second_version.status == "active"
        active_versions = (
            db_session.query(PlanVersion)
            .filter(PlanVersion.plan_tier_id == tier.id, PlanVersion.status == "active")
            .all()
        )
        assert len(active_versions) == 1
        assert active_versions[0].id == second_version.id

    def test_unknown_tier_raises_404(self, db_session):
        user = make_user(db_session)

        with pytest.raises(HTTPException) as exc_info:
            PlanService.set_price(db_session, "missing-tier-id", Decimal("100.00"), created_by=user.id)

        assert exc_info.value.status_code == 404
