from datetime import datetime
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from lumina.models import Unit
from lumina.schemas import UnitCreate, UnitUpdate
from lumina.services import unit_service


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def user_id():
    return uuid4()


@pytest.mark.asyncio
@patch('lumina.services.unit_service.unit_repo')
@patch('lumina.services.unit_service.audit_service')
async def test_create_unit_success(
    mock_audit, mock_repo, mock_session, user_id
):
    # Arrange
    mock_repo.get_by_name = AsyncMock(return_value=None)
    mock_repo.add = MagicMock()
    mock_audit.register_action = AsyncMock()
    unit_data = UnitCreate(name='Central', location='Main Building')

    # Act
    result = await unit_service.create_unit(mock_session, user_id, unit_data)

    # Assert
    assert result.name == 'Central'
    assert result.location == 'Main Building'
    assert result.created_by == user_id
    mock_repo.add.assert_called_once()
    mock_session.flush.assert_called_once()
    mock_audit.register_action.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch('lumina.services.unit_service.unit_repo')
async def test_create_unit_conflict(mock_repo, mock_session, user_id):
    # Arrange
    mock_repo.get_by_name = AsyncMock(
        return_value=Unit(name='Central', location='Other')
    )
    unit_data = UnitCreate(name='Central', location='Main Building')

    # Act / Assert
    with pytest.raises(HTTPException) as exc:
        await unit_service.create_unit(mock_session, user_id, unit_data)

    assert exc.value.status_code == HTTPStatus.CONFLICT
    assert exc.value.detail == 'Unit name already exists'
    mock_repo.add.assert_not_called()


@pytest.mark.asyncio
@patch('lumina.services.unit_service.unit_repo')
async def test_get_unit_by_id_success(mock_repo, mock_session):
    unit_id = uuid4()
    u = Unit(name='Test')
    u.id = unit_id
    mock_repo.get_by_id = AsyncMock(return_value=u)

    result = await unit_service.get_unit_by_id(mock_session, unit_id)
    assert result.id == unit_id
    assert result.name == 'Test'


@pytest.mark.asyncio
@patch('lumina.services.unit_service.unit_repo')
async def test_get_unit_by_id_not_found(mock_repo, mock_session):
    unit_id = uuid4()
    mock_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await unit_service.get_unit_by_id(mock_session, unit_id)

    assert exc.value.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@patch('lumina.services.unit_service.unit_repo')
@patch('lumina.services.unit_service.audit_service')
async def test_update_unit_success(
    mock_audit, mock_repo, mock_session, user_id
):
    unit_id = uuid4()
    db_unit = Unit(name='Old', location='Old Loc')
    db_unit.id = unit_id
    db_unit.created_at = datetime.utcnow()
    db_unit.updated_at = datetime.utcnow()

    mock_repo.get_by_id = AsyncMock(return_value=db_unit)
    mock_repo.get_by_name = AsyncMock(return_value=None)
    mock_audit.register_action = AsyncMock()

    update_data = UnitUpdate(id=unit_id, name='New', location='New Loc')

    result = await unit_service.update_unit(mock_session, user_id, update_data)

    assert result.name == 'New'
    assert result.location == 'New Loc'
    assert result.updated_by == user_id
    mock_audit.register_action.assert_called_once()
    mock_session.commit.assert_called_once()
