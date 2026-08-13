from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from lumina.models import Source
from lumina.schemas import SourceCreate, SourceUpdate
from lumina.schemas.source import SourceFilter
from lumina.services.source_service import (
    create_source,
    delete_source,
    get_source_by_id,
    get_sources,
    update_source,
)


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_source_repo(mocker):
    repo = mocker.patch('lumina.services.source_service.source_repo')
    repo.get_by_name = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.list_all = AsyncMock()
    return repo


@pytest.fixture
def mock_audit_service(mocker):
    audit = mocker.patch('lumina.services.source_service.audit_service')
    audit.register_action = AsyncMock()
    return audit


@pytest.fixture
def mock_storage(mocker):
    return AsyncMock()


@pytest.mark.asyncio
async def test_create_source_success(
    mock_session, mock_source_repo, mock_audit_service
):
    # Arrange
    user_id = uuid4()
    data = SourceCreate(name='Test Source', description='Test Description')
    mock_source_repo.get_by_name.return_value = None

    # Act
    source = await create_source(mock_session, user_id, data)

    # Assert
    assert source.name == 'Test Source'
    mock_source_repo.add.assert_called_once()
    mock_audit_service.register_action.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_source_conflict(mock_session, mock_source_repo):
    # Arrange
    user_id = uuid4()
    data = SourceCreate(name='Test Source', description='Test Description')
    mock_source_repo.get_by_name.return_value = Source(
        name='Test Source', description='Desc'
    )

    # Act & Assert
    with pytest.raises(HTTPException) as exc:
        await create_source(mock_session, user_id, data)
    assert exc.value.status_code == HTTPStatus.CONFLICT


@pytest.mark.asyncio
async def test_get_sources(mock_session, mock_source_repo):
    # Arrange
    filters = SourceFilter()
    s = Source(name='Test Source', description='Desc')
    s.id = uuid4()
    mock_source_repo.list_all.return_value = [s]

    # Act
    sources = await get_sources(mock_session, filters)

    # Assert
    assert len(sources) == 1
    mock_source_repo.list_all.assert_called_once_with(mock_session, filters)


@pytest.mark.asyncio
async def test_get_source_by_id_success(mock_session, mock_source_repo):
    # Arrange
    source_id = uuid4()
    s = Source(name='Test Source', description='Desc')
    s.id = source_id
    mock_source_repo.get_by_id.return_value = s

    # Act
    source = await get_source_by_id(mock_session, source_id)

    # Assert
    assert source.id == source_id


@pytest.mark.asyncio
async def test_get_source_by_id_not_found(mock_session, mock_source_repo):
    # Arrange
    source_id = uuid4()
    mock_source_repo.get_by_id.return_value = None

    # Act & Assert
    with pytest.raises(HTTPException) as exc:
        await get_source_by_id(mock_session, source_id)
    assert exc.value.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_update_source_success(
    mock_session, mock_source_repo, mock_audit_service
):
    # Arrange
    user_id = uuid4()
    source_id = uuid4()
    data = SourceUpdate(
        id=source_id, name='Updated Source', description='Updated Description'
    )

    db_source = Source(name='Old Source', description='Desc')
    db_source.id = source_id
    db_source.created_at = datetime.now(timezone.utc)
    mock_source_repo.get_by_id.return_value = db_source
    mock_source_repo.get_by_name.return_value = None

    # Act
    updated_source = await update_source(mock_session, user_id, data)

    # Assert
    assert updated_source.name == 'Updated Source'
    mock_audit_service.register_action.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_source_success(
    mock_session, mock_source_repo, mock_audit_service
):
    # Arrange
    user_id = uuid4()
    source_id = uuid4()

    db_source = Source(name='Old Source', description='Desc')
    db_source.id = source_id
    db_source.created_at = datetime.now(timezone.utc)
    mock_source_repo.get_by_id.return_value = db_source

    # Act
    await delete_source(mock_session, user_id, source_id)

    # Assert
    mock_audit_service.register_action.assert_called_once()
    mock_session.commit.assert_called_once()
