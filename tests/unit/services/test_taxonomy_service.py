import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from fastapi import HTTPException
from http import HTTPStatus
from datetime import datetime

from lumina.services import taxonomy_service
from lumina.schemas import TaxonomyCreate, TaxonomyUpdate
from lumina.models import Taxonomy, Typification

@pytest.fixture
def mock_session():
    return AsyncMock()

@pytest.fixture
def user_id():
    return uuid4()

@pytest.mark.asyncio
@patch('lumina.services.taxonomy_service.taxonomy_repo')
@patch('lumina.services.taxonomy_service.audit_service')
async def test_create_taxonomy_success(mock_audit, mock_repo, mock_session, user_id):
    # Arrange
    typification_id = uuid4()
    mock_repo.get_conflict = AsyncMock(return_value=None)
    mock_repo.get_typification = AsyncMock(return_value=Typification(name="Type 1"))
    mock_repo.add_taxonomy = MagicMock()
    mock_audit.register_action = AsyncMock()
    
    tax_data = TaxonomyCreate(title="Taxonomy 1", description="Desc 1", typification_id=typification_id, source_ids=[])
    
    # Act
    result = await taxonomy_service.create_taxonomy(mock_session, user_id, tax_data)
    
    # Assert
    assert result.title == "Taxonomy 1"
    assert result.description == "Desc 1"
    assert result.typification_id == typification_id
    mock_repo.add_taxonomy.assert_called_once()
    mock_session.flush.assert_called_once()
    mock_audit.register_action.assert_called_once()
    mock_session.commit.assert_called_once()

@pytest.mark.asyncio
@patch('lumina.services.taxonomy_service.taxonomy_repo')
async def test_create_taxonomy_conflict(mock_repo, mock_session, user_id):
    # Arrange
    typification_id = uuid4()
    mock_repo.get_conflict = AsyncMock(return_value=Taxonomy(title="Tax 1", description="Desc 1", typification_id=typification_id))
    
    tax_data = TaxonomyCreate(title="Tax 1", description="Desc 1", typification_id=typification_id, source_ids=[])
    
    # Act / Assert
    with pytest.raises(HTTPException) as exc:
        await taxonomy_service.create_taxonomy(mock_session, user_id, tax_data)
        
    assert exc.value.status_code == HTTPStatus.CONFLICT
    assert exc.value.detail == 'Taxonomy title already exists for this typification'
    mock_repo.add_taxonomy.assert_not_called()

@pytest.mark.asyncio
@patch('lumina.services.taxonomy_service.taxonomy_repo')
async def test_get_taxonomy_by_id_success(mock_repo, mock_session):
    tax_id = uuid4()
    t = Taxonomy(title="Test", description="", typification_id=uuid4())
    t.id = tax_id
    mock_repo.get_by_id = AsyncMock(return_value=t)
    
    result = await taxonomy_service.get_taxonomy_by_id(mock_session, tax_id)
    assert result.id == tax_id
    assert result.title == "Test"

@pytest.mark.asyncio
@patch('lumina.services.taxonomy_service.taxonomy_repo')
async def test_get_taxonomy_by_id_not_found(mock_repo, mock_session):
    tax_id = uuid4()
    mock_repo.get_by_id = AsyncMock(return_value=None)
    
    with pytest.raises(HTTPException) as exc:
        await taxonomy_service.get_taxonomy_by_id(mock_session, tax_id)
        
    assert exc.value.status_code == HTTPStatus.NOT_FOUND

@pytest.mark.asyncio
@patch('lumina.services.taxonomy_service.taxonomy_repo')
@patch('lumina.services.taxonomy_service.audit_service')
async def test_update_taxonomy_success(mock_audit, mock_repo, mock_session, user_id):
    tax_id = uuid4()
    typification_id = uuid4()
    
    db_tax = Taxonomy(title="Old", description="Old Desc", typification_id=typification_id)
    db_tax.id = tax_id
    db_tax.typification_id = typification_id
    db_tax.created_at = datetime.utcnow()
    db_tax.updated_at = datetime.utcnow()
    
    mock_repo.get_by_id = AsyncMock(return_value=db_tax)
    mock_repo.get_conflict = AsyncMock(return_value=None)
    mock_audit.register_action = AsyncMock()
    
    update_data = TaxonomyUpdate(id=tax_id, title="New", description="New Desc", typification_id=typification_id, source_ids=[])
    
    result = await taxonomy_service.update_taxonomy(mock_session, user_id, update_data)
    
    assert result.title == "New"
    assert result.description == "New Desc"
    assert result.updated_by == user_id
    mock_audit.register_action.assert_called_once()
    mock_session.commit.assert_called_once()
