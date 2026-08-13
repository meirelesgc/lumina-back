import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.models import Taxonomy, Typification
from lumina.repositories import taxonomy_repo
from lumina.schemas.taxonomy import TaxonomyFilter


@pytest.mark.asyncio
async def test_taxonomy_repo_get_by_id(session: AsyncSession):
    # Setup test data
    typ = Typification(name='Typification A')
    session.add(typ)
    await session.commit()
    await session.refresh(typ)

    tax = Taxonomy(title='Taxonomy A', description='', typification_id=typ.id)
    session.add(tax)
    await session.commit()
    await session.refresh(tax)

    result = await taxonomy_repo.get_by_id(session, tax.id)
    assert result is not None
    assert result.id == tax.id
    assert result.title == tax.title


@pytest.mark.asyncio
async def test_taxonomy_repo_get_conflict(session: AsyncSession):
    # Setup test data
    typ = Typification(name='Typification B')
    session.add(typ)
    await session.commit()
    await session.refresh(typ)

    tax = Taxonomy(
        title='Conflict Tax', description='', typification_id=typ.id
    )
    session.add(tax)
    await session.commit()
    await session.refresh(tax)

    result = await taxonomy_repo.get_conflict(session, 'Conflict Tax', typ.id)
    assert result is not None
    assert result.id == tax.id


@pytest.mark.asyncio
async def test_taxonomy_repo_list_all(session: AsyncSession):
    # Setup test data
    typ = Typification(name='Typification C')
    session.add(typ)
    await session.commit()
    await session.refresh(typ)

    t1 = Taxonomy(title='Alpha', description='', typification_id=typ.id)
    t2 = Taxonomy(title='Beta', description='', typification_id=typ.id)
    session.add_all([t1, t2])
    await session.commit()

    # Test without filters
    filters = TaxonomyFilter(offset=0, limit=10)
    results = await taxonomy_repo.list_all(session, filters)
    assert len(results) >= 2

    # Test with text search
    filters_search = TaxonomyFilter(offset=0, limit=10, q='Alpha')
    results_search = await taxonomy_repo.list_all(session, filters_search)
    assert len(results_search) == 1
    assert results_search[0].title == 'Alpha'
