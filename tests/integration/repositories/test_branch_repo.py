import pytest

from lumina.repositories import branch_repo
from lumina.schemas import BranchFilter
from tests.factories.branch_factory import (
    BranchFactory,
    TaxonomyFactory,
    TypificationFactory,
)


@pytest.mark.asyncio
async def test_branch_repo_list_all(session, user):
    # Arrange
    typ = TypificationFactory()
    typ.set_creation_audit(user.id)
    session.add(typ)
    await session.commit()

    tax = TaxonomyFactory(typification_id=typ.id)
    tax.set_creation_audit(user.id)
    session.add(tax)
    await session.commit()

    branch1 = BranchFactory(title='Branch 1', taxonomy_id=tax.id)
    branch1.set_creation_audit(user.id)
    branch2 = BranchFactory(title='Branch 2', taxonomy_id=tax.id)
    branch2.set_creation_audit(user.id)

    session.add_all([branch1, branch2])
    await session.commit()

    # Act
    filters = BranchFilter(q='Branch')
    results = await branch_repo.list_all(session, filters)

    # Assert
    assert len(results) >= 2
    titles = [b.title for b in results]
    assert 'Branch 1' in titles
    assert 'Branch 2' in titles


@pytest.mark.asyncio
async def test_branch_repo_get_by_id(session, user):
    typ = TypificationFactory()
    typ.set_creation_audit(user.id)
    session.add(typ)
    await session.commit()

    tax = TaxonomyFactory(typification_id=typ.id)
    tax.set_creation_audit(user.id)
    session.add(tax)
    await session.commit()

    branch = BranchFactory(title='Get By ID', taxonomy_id=tax.id)
    branch.set_creation_audit(user.id)
    session.add(branch)
    await session.commit()

    result = await branch_repo.get_by_id(session, branch.id)
    assert result is not None
    assert result.id == branch.id
    assert result.title == 'Get By ID'
