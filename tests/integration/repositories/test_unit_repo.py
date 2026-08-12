import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.repositories import unit_repo
from lumina.schemas import UnitFilter
from lumina.models import Unit

@pytest.mark.asyncio
async def test_unit_repo_get_by_id(session: AsyncSession, unit: Unit):
    result = await unit_repo.get_by_id(session, unit.id)
    assert result is not None
    assert result.id == unit.id
    assert result.name == unit.name

@pytest.mark.asyncio
async def test_unit_repo_get_by_name(session: AsyncSession, unit: Unit):
    result = await unit_repo.get_by_name(session, unit.name)
    assert result is not None
    assert result.id == unit.id

@pytest.mark.asyncio
async def test_unit_repo_get_by_name_exclude_id(session: AsyncSession, unit: Unit):
    result = await unit_repo.get_by_name(session, unit.name, exclude_id=unit.id)
    assert result is None

@pytest.mark.asyncio
async def test_unit_repo_list_all(session: AsyncSession):
    # Setup test data
    from lumina.models import Unit
    u1 = Unit(name="Alpha", location="Loc A")
    u2 = Unit(name="Beta", location="Loc B")
    session.add_all([u1, u2])
    await session.commit()
    await session.refresh(u1)
    await session.refresh(u2)
    
    # Test without filters
    filters = UnitFilter(offset=0, limit=10)
    results = await unit_repo.list_all(session, filters)
    assert len(results) >= 2
    
    # Test with text search
    filters_search = UnitFilter(offset=0, limit=10, q="Alpha")
    results_search = await unit_repo.list_all(session, filters_search)
    assert len(results_search) == 1
    assert results_search[0].name == "Alpha"
