from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from lumina.models import AccessType, Advisorship, User
from lumina.schemas.advisorship import (
    AdvisorshipCreate,
    AdvisorshipRoleType,
    AdvisorshipStatus,
    AdvisorshipUpdate,
)
from lumina.services import advisorship_service


@pytest.fixture
def session():
    return AsyncMock()


@pytest.fixture
def mock_advisorship_repo(mocker):
    repo = mocker.patch('lumina.services.advisorship_service.advisorship_repo')
    repo.get_by_id = AsyncMock()
    repo.get_active_pair = AsyncMock()
    repo.add_advisorship = MagicMock()
    repo.list_all = AsyncMock()
    repo.list_by_advisor = AsyncMock()
    repo.list_by_advisee = AsyncMock()
    repo.get_advisee_document_metrics = AsyncMock()
    repo.get_advisee_documents = AsyncMock()
    return repo


@pytest.fixture
def mock_user_repo(mocker):
    repo = mocker.patch('lumina.services.advisorship_service.user_repo')
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_project_repo(mocker):
    repo = mocker.patch('lumina.services.advisorship_service.project_repo')
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_audit_service(mocker):
    audit = mocker.patch('lumina.services.advisorship_service.audit_service')
    audit.register_action = AsyncMock()
    return audit


@pytest.mark.asyncio
async def test_create_advisorship_success(
    session,
    mock_advisorship_repo,
    mock_user_repo,
    mock_audit_service,
):
    current_user = MagicMock(
        spec=User, id=uuid4(), access_level=AccessType.DEFAULT
    )
    advisor = MagicMock(spec=User, id=uuid4(), deleted_at=None)
    advisee = MagicMock(spec=User, id=uuid4(), deleted_at=None)

    mock_user_repo.get_by_id.side_effect = (
        lambda s, uid: advisor if uid == advisor.id else advisee
    )
    mock_advisorship_repo.get_active_pair.return_value = None

    data = AdvisorshipCreate(
        advisor_id=advisor.id,
        advisee_id=advisee.id,
        role_type=AdvisorshipRoleType.MAIN_ADVISOR,
        topic='TCC em Inteligência Artificial',
    )

    result = await advisorship_service.create_advisorship(
        session, current_user, data
    )

    assert result.advisor_id == advisor.id
    assert result.advisee_id == advisee.id
    assert result.topic == 'TCC em Inteligência Artificial'
    mock_advisorship_repo.add_advisorship.assert_called_once()
    mock_audit_service.register_action.assert_called_once()


@pytest.mark.asyncio
async def test_create_advisorship_self_advisor_error(session):
    user_id = uuid4()
    current_user = MagicMock(spec=User, id=user_id)
    data = AdvisorshipCreate(
        advisor_id=user_id,
        advisee_id=user_id,
    )

    with pytest.raises(HTTPException) as exc:
        await advisorship_service.create_advisorship(
            session, current_user, data
        )
    assert exc.value.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
async def test_create_advisorship_conflict(
    session, mock_advisorship_repo, mock_user_repo
):
    current_user = MagicMock(spec=User, id=uuid4())
    advisor = MagicMock(spec=User, id=uuid4(), deleted_at=None)
    advisee = MagicMock(spec=User, id=uuid4(), deleted_at=None)

    mock_user_repo.get_by_id.side_effect = (
        lambda s, uid: advisor if uid == advisor.id else advisee
    )
    mock_advisorship_repo.get_active_pair.return_value = MagicMock(
        spec=Advisorship
    )

    data = AdvisorshipCreate(
        advisor_id=advisor.id,
        advisee_id=advisee.id,
    )

    with pytest.raises(HTTPException) as exc:
        await advisorship_service.create_advisorship(
            session, current_user, data
        )
    assert exc.value.status_code == HTTPStatus.CONFLICT


@pytest.mark.asyncio
async def test_get_advisorship_by_id_forbidden(session, mock_advisorship_repo):
    current_user = MagicMock(
        spec=User, id=uuid4(), access_level=AccessType.DEFAULT
    )
    advisorship = MagicMock(
        spec=Advisorship,
        id=uuid4(),
        advisor_id=uuid4(),
        advisee_id=uuid4(),
        deleted_at=None,
    )
    mock_advisorship_repo.get_by_id.return_value = advisorship

    with pytest.raises(HTTPException) as exc:
        await advisorship_service.get_advisorship_by_id(
            session, current_user, advisorship.id
        )
    assert exc.value.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_update_advisorship_success(
    session, mock_advisorship_repo, mock_audit_service
):
    advisor_id = uuid4()
    current_user = MagicMock(
        spec=User, id=advisor_id, access_level=AccessType.DEFAULT
    )
    advisorship = MagicMock(
        spec=Advisorship,
        id=uuid4(),
        advisor_id=advisor_id,
        advisee_id=uuid4(),
        project_id=None,
        role_type='MAIN_ADVISOR',
        topic='Antigo Tema',
        status='ACTIVE',
        created_at=MagicMock(),
        updated_at=None,
        advisor=None,
        advisee=None,
        project=None,
        deleted_at=None,
    )
    mock_advisorship_repo.get_by_id.return_value = advisorship

    update_data = AdvisorshipUpdate(
        topic='Novo Tema de TCC',
        status=AdvisorshipStatus.COMPLETED,
    )

    result = await advisorship_service.update_advisorship(
        session, current_user, advisorship.id, update_data
    )

    assert result.topic == 'Novo Tema de TCC'
    assert result.status == 'COMPLETED'
    mock_audit_service.register_action.assert_called_once()


@pytest.mark.asyncio
async def test_delete_advisorship_success(
    session, mock_advisorship_repo, mock_audit_service
):
    advisor_id = uuid4()
    current_user = MagicMock(
        spec=User, id=advisor_id, access_level=AccessType.DEFAULT
    )
    advisorship = MagicMock(
        spec=Advisorship,
        id=uuid4(),
        advisor_id=advisor_id,
        advisee_id=uuid4(),
        project_id=None,
        role_type='MAIN_ADVISOR',
        topic='Tema',
        status='ACTIVE',
        created_at=MagicMock(),
        updated_at=None,
        advisor=None,
        advisee=None,
        project=None,
        deleted_at=None,
    )
    mock_advisorship_repo.get_by_id.return_value = advisorship

    await advisorship_service.delete_advisorship(
        session, current_user, advisorship.id
    )

    mock_audit_service.register_action.assert_called_once()
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_my_advisees(session, mock_advisorship_repo):
    current_user = MagicMock(spec=User, id=uuid4())
    advisee_user = MagicMock(
        spec=User,
        id=uuid4(),
        username='orientando_1',
        email='aluno@teste.com',
        phone_number='5501999999999',
        access_level=AccessType.DEFAULT,
        created_at=MagicMock(),
        updated_at=None,
        icon=None,
    )
    rel = MagicMock(
        spec=Advisorship,
        id=uuid4(),
        advisee_id=advisee_user.id,
        advisee=advisee_user,
        role_type='MAIN_ADVISOR',
        topic='TCC Robótica',
        status='ACTIVE',
        project=None,
    )

    mock_advisorship_repo.list_by_advisor.return_value = [rel]
    expected_total_docs = 3
    expected_pending = 1
    mock_advisorship_repo.get_advisee_document_metrics.return_value = {
        'total': expected_total_docs,
        'pending': expected_pending,
    }

    cards = await advisorship_service.get_my_advisees(session, current_user)

    assert len(cards) == 1
    assert cards[0].advisee.username == 'orientando_1'
    assert cards[0].total_documents == expected_total_docs
    assert cards[0].pending_reviews == expected_pending
