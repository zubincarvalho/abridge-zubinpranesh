"""InMemoryCaseRepository behavior against the frozen CaseRepository port."""

import pytest

from app.adapters import DEMO_FIXTURE_ID, FixtureProvider
from app.contracts import AuthLensCase, CaseStatus
from app.ports import case_repository
from app.repositories import (
    CaseAlreadyExistsError,
    CaseNotFoundError,
    InMemoryCaseRepository,
)


@pytest.fixture(scope="module")
def provider() -> FixtureProvider:
    return FixtureProvider()


@pytest.fixture()
def case(provider) -> AuthLensCase:
    return provider.build_case(DEMO_FIXTURE_ID, case_id="case-demo-001")


@pytest.fixture()
def repo() -> InMemoryCaseRepository:
    return InMemoryCaseRepository()


def test_satisfies_the_port_protocol(repo):
    # CaseRepository is not @runtime_checkable; verify the surface directly.
    port_methods = [
        name
        for name in vars(case_repository.CaseRepository)
        if not name.startswith("_")
    ]
    assert port_methods, "port unexpectedly empty"
    for name in port_methods:
        assert callable(getattr(repo, name)), f"missing port method {name}"


def test_create_and_get_round_trip(repo, case):
    created = repo.create(case)
    assert created == case
    assert repo.get(case.case_id) == case
    assert repo.list_case_ids() == [case.case_id]


def test_create_duplicate_raises(repo, case):
    repo.create(case)
    with pytest.raises(CaseAlreadyExistsError, match="case-demo-001"):
        repo.create(case)


def test_get_missing_raises(repo):
    with pytest.raises(CaseNotFoundError, match="case-ghost"):
        repo.get("case-ghost")


def test_save_replaces_whole_case(repo, case):
    repo.create(case)
    updated = case.model_copy(update={"status": CaseStatus.ANALYZING})
    repo.save(updated)
    assert repo.get(case.case_id).status == CaseStatus.ANALYZING


def test_save_unknown_case_raises(repo, case):
    with pytest.raises(CaseNotFoundError, match=case.case_id):
        repo.save(case)


def test_returned_cases_are_isolated_copies(repo, case):
    repo.create(case)
    fetched = repo.get(case.case_id)
    fetched.patient.chart_items.clear()
    fetched.clinical_indication = "TAMPERED"
    stored = repo.get(case.case_id)
    assert stored.patient.chart_items
    assert stored.clinical_indication == case.clinical_indication


def test_mutating_input_after_create_does_not_affect_store(repo, case):
    repo.create(case)
    case.patient.chart_items.clear()
    assert repo.get(case.case_id).patient.chart_items


def test_reset_clears_everything(repo, case):
    repo.create(case)
    repo.reset()
    assert repo.list_case_ids() == []
    with pytest.raises(CaseNotFoundError):
        repo.get(case.case_id)
    # Repository is usable again after reset.
    repo.create(case)
    assert repo.list_case_ids() == [case.case_id]
