from datetime import datetime
from http import HTTPStatus
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from lumina.schemas.project import ProjectCreate, ProjectUpdate
from lumina.services import project_service
from tests.factories.project_factory import ProjectFactory


@pytest.fixture
def session():
    return AsyncMock()


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def project_mock():
    project = ProjectFactory.build(id=uuid4(), created_at=datetime.utcnow())
    project.deleted_at = None
    return project


@pytest.fixture
def mock_project_repo(mocker):
    repo = mocker.patch('lumina.services.project_service.project_repo')
    repo.get_by_name = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.update_document_project_names = AsyncMock()
    return repo


@pytest.fixture
def mock_audit_service(mocker):
    audit = mocker.patch('lumina.services.project_service.audit_service')
    audit.register_action = AsyncMock()
    return audit


@pytest.mark.asyncio
async def test_create_project_success(
    mock_audit_service, mock_project_repo, session, user_id
):
    mock_project_repo.get_by_name.return_value = None
    data = ProjectCreate(name='New Project', description='Test')

    result = await project_service.create_project(session, user_id, data)

    assert result.name == 'New Project'
    mock_project_repo.add_project.assert_called_once()
    mock_audit_service.register_action.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_project_conflict(
    mock_project_repo, session, user_id, project_mock
):
    mock_project_repo.get_by_name.return_value = project_mock
    data = ProjectCreate(name='New Project')

    with pytest.raises(HTTPException) as exc:
        await project_service.create_project(session, user_id, data)

    assert exc.value.status_code == HTTPStatus.CONFLICT


@pytest.mark.asyncio
async def test_get_project_by_id_success(
    mock_project_repo, session, project_mock
):
    mock_project_repo.get_by_id.return_value = project_mock

    result = await project_service.get_project_by_id(session, project_mock.id)
    assert result == project_mock


@pytest.mark.asyncio
async def test_get_project_by_id_not_found(mock_project_repo, session):
    mock_project_repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await project_service.get_project_by_id(session, uuid4())

    assert exc.value.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_update_project_success(
    mock_audit_service, mock_project_repo, session, user_id, project_mock
):
    mock_project_repo.get_by_id.return_value = project_mock
    mock_project_repo.get_by_name.return_value = None
    data = ProjectUpdate(id=project_mock.id, name='Updated Name')

    result = await project_service.update_project(session, user_id, data)

    assert result.name == 'Updated Name'
    mock_audit_service.register_action.assert_awaited_once()
    mock_project_repo.update_document_project_names.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_project_success(
    mock_audit_service, mock_project_repo, session, user_id, project_mock
):
    mock_project_repo.get_by_id.return_value = project_mock

    await project_service.delete_project(session, user_id, project_mock.id)

    assert project_mock.deleted_at is not None
    mock_audit_service.register_action.assert_awaited_once()
