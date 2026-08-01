"""Unit tests for the versioned contract template lineage (D2)."""

from datetime import UTC, datetime

from app.models import ContractTemplateVersion
from app.services import ContractTemplateService
from tests.unit.conftest import make_contract_template_version, make_user


class TestCreateVersion:
    def test_first_version_becomes_active(self, db_session):
        user = make_user(db_session)

        version = ContractTemplateService.create_version(db_session, "Corpo v1", datetime.now(UTC), user.id)

        assert version.status == "active"
        assert ContractTemplateService.get_active_version(db_session).id == version.id

    def test_new_version_supersedes_the_prior_active_one(self, db_session):
        user = make_user(db_session)
        first = make_contract_template_version(db_session, created_by=user.id)

        second = ContractTemplateService.create_version(db_session, "Corpo v2", datetime.now(UTC), user.id)

        db_session.refresh(first)
        assert first.status == "superseded"
        active_versions = (
            db_session.query(ContractTemplateVersion).filter(ContractTemplateVersion.status == "active").all()
        )
        assert len(active_versions) == 1
        assert active_versions[0].id == second.id

    def test_get_history_returns_most_recent_first(self, db_session):
        user = make_user(db_session)
        make_contract_template_version(db_session, created_by=user.id, body="v1")
        second = ContractTemplateService.create_version(db_session, "v2", datetime.now(UTC), user.id)

        history = ContractTemplateService.get_history(db_session)

        assert history[0].id == second.id
        assert len(history) == 2

    def test_get_active_version_returns_none_when_no_template_exists(self, db_session):
        assert ContractTemplateService.get_active_version(db_session) is None

    def test_get_history_breaks_created_at_ties_deterministically(self, db_session):
        """MySQL's whole-second DATETIME made two same-second creates order
        arbitrarily (the ContractTemplatesPage e2e flake); id is the
        documented tiebreaker, so an exact tie is still ordered predictably.
        """
        user = make_user(db_session)
        tied_timestamp = datetime.now(UTC)
        first = make_contract_template_version(db_session, created_by=user.id, created_at=tied_timestamp)
        second = make_contract_template_version(db_session, created_by=user.id, created_at=tied_timestamp)

        history = ContractTemplateService.get_history(db_session)

        expected_order = sorted([first.id, second.id], reverse=True)
        assert [v.id for v in history] == expected_order
