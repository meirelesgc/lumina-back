import pytest

from lumina.models import BranchQueryExpansion
from lumina.repositories import branch_query_expansion_repo
from tests.factories.branch_factory import (
    BranchFactory,
    TaxonomyFactory,
    TypificationFactory,
)

EXPECTED_ACTIVE_COUNT_TWO = 2


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


def _make_expansion(branch_id, version, is_active=True, text='Texto'):
    expansion = BranchQueryExpansion(
        branch_id=branch_id,
        expansion_text=text,
        expansion_type='paraphrase',
        generation_model='mock-model',
        generation_version=version,
        is_active=is_active,
    )
    return expansion


@pytest.mark.asyncio
async def test_list_active_grouped_returns_only_active(session, user):
    branch = await _create_branch(session, user)

    active_1 = _make_expansion(branch.id, version=2, text='Ativa 1')
    active_2 = _make_expansion(branch.id, version=2, text='Ativa 2')
    inactive = _make_expansion(
        branch.id, version=1, is_active=False, text='Inativa'
    )
    session.add_all([active_1, active_2, inactive])
    await session.commit()

    grouped = await branch_query_expansion_repo.list_active_grouped(
        session, [branch.id]
    )

    assert len(grouped[branch.id]) == EXPECTED_ACTIVE_COUNT_TWO
    texts = {e.expansion_text for e in grouped[branch.id]}
    assert texts == {'Ativa 1', 'Ativa 2'}


@pytest.mark.asyncio
async def test_list_active_grouped_empty_branch_ids(session):
    grouped = await branch_query_expansion_repo.list_active_grouped(
        session, []
    )
    assert grouped == {}


@pytest.mark.asyncio
async def test_deactivate_active(session, user):
    branch = await _create_branch(session, user)
    expansion = _make_expansion(branch.id, version=1)
    session.add(expansion)
    await session.commit()

    await branch_query_expansion_repo.deactivate_active(session, branch.id)
    await session.commit()

    grouped = await branch_query_expansion_repo.list_active_grouped(
        session, [branch.id]
    )
    assert grouped.get(branch.id, []) == []


@pytest.mark.asyncio
async def test_get_latest_generation_version(session, user):
    branch = await _create_branch(session, user)

    assert (
        await branch_query_expansion_repo.get_latest_generation_version(
            session, branch.id
        )
        == 0
    )

    session.add(_make_expansion(branch.id, version=1, is_active=False))
    session.add(_make_expansion(branch.id, version=2))
    await session.commit()

    latest = await branch_query_expansion_repo.get_latest_generation_version(
        session, branch.id
    )
    assert latest == EXPECTED_ACTIVE_COUNT_TWO
