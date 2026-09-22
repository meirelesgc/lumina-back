import pytest

from lumina.models import BranchSectionRequirement
from lumina.repositories import branch_section_requirement_repo
from tests.factories.branch_factory import (
    BranchFactory,
    TaxonomyFactory,
    TypificationFactory,
)

EXPECTED_GENERATION_VERSION_TWO = 2


async def _create_branch(session, user):
    typ = TypificationFactory()
    typ.set_creation_audit(user.id)
    session.add(typ)
    await session.commit()

    tax = TaxonomyFactory(typification_id=typ.id)
    tax.set_creation_audit(user.id)
    session.add(tax)
    await session.commit()

    branch = BranchFactory(taxonomy_id=tax.id)
    branch.set_creation_audit(user.id)
    session.add(branch)
    await session.commit()

    return branch


def _make_requirement(branch_id, version, is_active=True, scope='UNKNOWN'):
    return BranchSectionRequirement(
        branch_id=branch_id,
        scope=scope,
        generation_model='mock-model',
        generation_version=version,
        expected_section=None,
        reasoning=None,
        is_active=is_active,
    )


@pytest.mark.asyncio
async def test_get_active_grouped_returns_only_active(session, user):
    branch = await _create_branch(session, user)

    active = _make_requirement(branch.id, version=2, scope='SPECIFIC_SECTION')
    inactive = _make_requirement(branch.id, version=1, is_active=False)
    session.add_all([inactive, active])
    await session.commit()

    grouped = await branch_section_requirement_repo.get_active_grouped(
        session, [branch.id]
    )

    assert grouped[branch.id].scope == 'SPECIFIC_SECTION'
    assert (
        grouped[branch.id].generation_version
        == EXPECTED_GENERATION_VERSION_TWO
    )


@pytest.mark.asyncio
async def test_get_active_grouped_empty_branch_ids(session):
    grouped = await branch_section_requirement_repo.get_active_grouped(
        session, []
    )
    assert grouped == {}


@pytest.mark.asyncio
async def test_deactivate_active(session, user):
    branch = await _create_branch(session, user)
    session.add(_make_requirement(branch.id, version=1))
    await session.commit()

    await branch_section_requirement_repo.deactivate_active(session, branch.id)
    await session.commit()

    grouped = await branch_section_requirement_repo.get_active_grouped(
        session, [branch.id]
    )
    assert branch.id not in grouped


@pytest.mark.asyncio
async def test_get_latest_generation_version(session, user):
    branch = await _create_branch(session, user)

    assert (
        await branch_section_requirement_repo.get_latest_generation_version(
            session, branch.id
        )
        == 0
    )

    session.add(_make_requirement(branch.id, version=1, is_active=False))
    session.add(_make_requirement(branch.id, version=2))
    await session.commit()

    latest = (
        await branch_section_requirement_repo.get_latest_generation_version(
            session, branch.id
        )
    )
    assert latest == EXPECTED_GENERATION_VERSION_TWO
