"""Business rules for the legal contract template's versioned lineage (D2)."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import ContractTemplateVersion


class ContractTemplateService:
    """Author and version the contract template body, mirroring ``PlanService.set_price``."""

    @staticmethod
    def get_active_version(db: Session) -> ContractTemplateVersion | None:
        """Return the current active template version, if any."""
        return db.query(ContractTemplateVersion).filter(ContractTemplateVersion.status == "active").first()

    @staticmethod
    def get_history(db: Session) -> list[ContractTemplateVersion]:
        """Return the full template version history, most recent first.

        Orders by created_at with id as a tiebreaker: without a secondary key,
        rows created within the same DB timestamp resolution have no
        guaranteed order, which is exactly what made this query flaky (see
        TimestampMixin's fsp=6 precision -- that shrinks the tie window, this
        makes ties (of any width) deterministic).
        """
        return (
            db.query(ContractTemplateVersion)
            .order_by(ContractTemplateVersion.created_at.desc(), ContractTemplateVersion.id.desc())
            .all()
        )

    @staticmethod
    def create_version(db: Session, body: str, effective_from: datetime, created_by: str) -> ContractTemplateVersion:
        """Create and activate a new template version, superseding the previous one."""
        previous = ContractTemplateService.get_active_version(db)
        if previous:
            previous.status = "superseded"

        version = ContractTemplateVersion(
            body=body,
            status="active",
            effective_from=effective_from,
            created_by=created_by,
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version
