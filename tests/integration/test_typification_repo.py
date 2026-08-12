import pytest
from lumina.repositories import typification_repo
from lumina.schemas.typification import TypificationFilter
from tests.factories.typification_factory import TypificationFactory

@pytest.mark.asyncio
async def test_create_and_get_typification(session):
    typ = TypificationFactory(name="Repo Typification")
    session.add(typ)
    await session.commit()
    
    result = await typification_repo.get_by_name(session, "Repo Typification")
    assert result is not None
    assert result.id == typ.id

@pytest.mark.asyncio
async def test_list_all_typifications(session):
    typ1 = TypificationFactory(name="List Typification 1")
    typ2 = TypificationFactory(name="List Typification 2")
    session.add(typ1)
    session.add(typ2)
    await session.commit()
    
    filters = TypificationFilter(limit=10, offset=0)
    results = await typification_repo.list_all(session, filters)
    
    assert len(results) >= 2
    names = [r.name for r in results]
    assert "List Typification 1" in names
    assert "List Typification 2" in names
