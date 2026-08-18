"""
Template: Teste Unitário (Service)

Foco: Decisões e regras de negócio.
Isola o banco de dados e dependências externas usando mocks.
"""

from http import HTTPStatus
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from lumina.models import Project
from lumina.schemas.project import ProjectCreate
from lumina.services import project_service


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_project_repo(mocker):
    repo = mocker.patch('lumina.services.project_service.project_repo')
    repo.get_by_name = AsyncMock()
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_audit_service(mocker):
    audit = mocker.patch('lumina.services.project_service.audit_service')
    audit.register_action = AsyncMock()
    return audit


@pytest.mark.asyncio
async def test_create_project_success(
    mock_session, mock_project_repo, mock_audit_service
):
    """
    Comportamento esperado (Happy Path) isolado com mocks.
    """
    mock_project_repo.get_by_name.return_value = None
    data = ProjectCreate(name='Novo Projeto', description='Descricao')
    user_id = uuid4()

    result = await project_service.create_project(mock_session, user_id, data)

    assert result.name == 'Novo Projeto'
    mock_project_repo.add_project.assert_called_once()
    mock_audit_service.register_action.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_project_conflict(mock_session, mock_project_repo):
    """
    Exemplo de Branch Coverage: Caso de Erro de negócio (Conflito 409).
    """
    existing_project = Project(name='Novo Projeto')
    mock_project_repo.get_by_name.return_value = existing_project
    data = ProjectCreate(name='Novo Projeto')
    user_id = uuid4()

    with pytest.raises(HTTPException) as exc:
        await project_service.create_project(mock_session, user_id, data)

    assert exc.value.status_code == HTTPStatus.CONFLICT
