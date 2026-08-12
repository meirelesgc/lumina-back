import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from http import HTTPStatus
from fastapi import HTTPException
from lumina.services import branch_service
from lumina.schemas import BranchCreate, BranchUpdate, BranchPublic

@pytest.fixture
def session():
    return AsyncMock()

@pytest.fixture
def mock_branch_repo(mocker):
    repo = mocker.patch("lumina.services.branch_service.branch_repo")
    repo.get_by_title_and_taxonomy = AsyncMock()
    repo.get_taxonomy = AsyncMock()
    repo.list_all = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_id_by_id = AsyncMock()
    return repo

@pytest.fixture
def mock_audit_service(mocker):
    audit = mocker.patch("lumina.services.branch_service.audit_service")
    audit.register_action = AsyncMock()
    return audit

@pytest.mark.asyncio
async def test_create_branch_success(session, mock_branch_repo, mock_audit_service):
    # Arrange
    user_id = uuid4()
    taxonomy_id = uuid4()
    data = BranchCreate(title="New Branch", description="Desc", taxonomy_id=taxonomy_id)
    
    mock_branch_repo.get_by_title_and_taxonomy.return_value = None
    mock_taxonomy = MagicMock(deleted_at=None)
    mock_branch_repo.get_taxonomy.return_value = mock_taxonomy
    
    # Act
    branch = await branch_service.create_branch(session, user_id, data)
    
    # Assert
    assert branch.title == "New Branch"
    mock_branch_repo.add.assert_called_once()
    mock_audit_service.register_action.assert_called_once()

@pytest.mark.asyncio
async def test_create_branch_conflict(session, mock_branch_repo):
    user_id = uuid4()
    taxonomy_id = uuid4()
    data = BranchCreate(title="New Branch", description="Desc", taxonomy_id=taxonomy_id)
    
    mock_branch_repo.get_by_title_and_taxonomy.return_value = MagicMock()
    
    with pytest.raises(HTTPException) as exc:
        await branch_service.create_branch(session, user_id, data)
    
    assert exc.value.status_code == HTTPStatus.CONFLICT

@pytest.mark.asyncio
async def test_create_branch_taxonomy_not_found(session, mock_branch_repo):
    user_id = uuid4()
    taxonomy_id = uuid4()
    data = BranchCreate(title="New Branch", description="Desc", taxonomy_id=taxonomy_id)
    
    mock_branch_repo.get_by_title_and_taxonomy.return_value = None
    mock_branch_repo.get_taxonomy.return_value = None
    
    with pytest.raises(HTTPException) as exc:
        await branch_service.create_branch(session, user_id, data)
    
    assert exc.value.status_code == HTTPStatus.NOT_FOUND

@pytest.mark.asyncio
async def test_get_branches(session, mock_branch_repo):
    filters = MagicMock()
    mock_branch_repo.list_all.return_value = []
    
    result = await branch_service.get_branches(session, filters)
    assert result == []
    mock_branch_repo.list_all.assert_called_once_with(session, filters)

@pytest.mark.asyncio
async def test_get_branch_by_id_success(session, mock_branch_repo):
    branch_id = uuid4()
    mock_branch = MagicMock(deleted_at=None)
    mock_branch_repo.get_by_id.return_value = mock_branch
    
    result = await branch_service.get_branch_by_id(session, branch_id)
    assert result == mock_branch

@pytest.mark.asyncio
async def test_get_branch_by_id_not_found(session, mock_branch_repo):
    branch_id = uuid4()
    mock_branch_repo.get_by_id.return_value = None
    mock_branch_repo.get_id_by_id.return_value = None
    
    with pytest.raises(HTTPException) as exc:
        await branch_service.get_branch_by_id(session, branch_id)
    
    assert exc.value.status_code == HTTPStatus.NOT_FOUND

@pytest.mark.asyncio
async def test_update_branch_success(session, mock_branch_repo, mock_audit_service):
    user_id = uuid4()
    branch_id = uuid4()
    taxonomy_id = uuid4()
    data = BranchUpdate(id=branch_id, title="Updated Branch", description="Updated Desc", taxonomy_id=taxonomy_id)
    
    db_branch = MagicMock(id=branch_id, title="Old Branch", description="Old Desc", taxonomy_id=taxonomy_id, deleted_at=None)
    mock_branch_repo.get_by_id.return_value = db_branch
    mock_branch_repo.get_by_title_and_taxonomy.return_value = None
    mock_branch_repo.get_taxonomy.return_value = MagicMock(deleted_at=None)
    
    result = await branch_service.update_branch(session, user_id, data)
    
    assert result.title == "Updated Branch"
    mock_audit_service.register_action.assert_called_once()

@pytest.mark.asyncio
async def test_delete_branch_success(session, mock_branch_repo, mock_audit_service):
    user_id = uuid4()
    branch_id = uuid4()
    taxonomy_id = uuid4()
    
    db_branch = MagicMock(id=branch_id, title="Branch to Delete", description="Desc", taxonomy_id=taxonomy_id, deleted_at=None)
    mock_branch_repo.get_by_id.return_value = db_branch
    
    await branch_service.delete_branch(session, user_id, branch_id)
    
    db_branch.set_deletion_audit.assert_called_once_with(user_id)
    mock_audit_service.register_action.assert_called_once()
