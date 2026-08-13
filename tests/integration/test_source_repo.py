import pytest

from lumina.repositories.source_repo import (
    add,
    get_by_id,
    get_by_name,
    list_all,
)
from lumina.schemas.source import SourceFilter
from tests.factories.source_factory import SourceFactory


@pytest.mark.asyncio
async def test_repo_add_and_get_by_id(session):
    # Arrange
    source = SourceFactory.build()
    add(session, source)
    await session.commit()
    await session.refresh(source)

    # Act
    fetched = await get_by_id(session, source.id)

    # Assert
    assert fetched is not None
    assert fetched.id == source.id


@pytest.mark.asyncio
async def test_repo_get_by_name(session):
    # Arrange
    source = SourceFactory.build(name='Unique Name')
    add(session, source)
    await session.commit()

    # Act
    fetched = await get_by_name(session, 'Unique Name')

    # Assert
    assert fetched is not None
    assert fetched.name == 'Unique Name'


@pytest.mark.asyncio
async def test_repo_list_all(session):
    # Arrange
    source1 = SourceFactory.build(name='Source A')
    source2 = SourceFactory.build(name='Source B')
    add(session, source1)
    add(session, source2)
    await session.commit()

    # Act
    filters = SourceFilter(limit=10, offset=0)
    results = await list_all(session, filters)

    # Assert
    assert len(results) >= 2
