from http import HTTPStatus
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from lumina.models import User
from lumina.schemas.user import AccessType


@pytest.mark.asyncio
async def test_characterization_document_crud_flow(client, token):
    """
    Caracterização do fluxo de criação, leitura e listagem de documentos.
    Fotografa o comportamento da API antes de qualquer refatoração.
    """
    doc_payload = {
        'name': 'Edital Caracterizacao 001',
        'identifier': f'EDITAL-{uuid4().hex[:6]}',
        'description': 'Descricao de teste para caracterizacao',
        'grupo': 'Grupo A',
        'tipo_documento': 'Edital',
        'projeto_nome': 'Projeto Lumina',
        'typification_ids': None,
        'editors_ids': None,
    }

    # 1. Criação do documento (POST /doc)
    response_create = client.post(
        '/doc',
        headers={'Authorization': f'Bearer {token}'},
        json=doc_payload,
    )
    assert response_create.status_code == HTTPStatus.CREATED
    created_doc = response_create.json()
    assert 'id' in created_doc
    assert created_doc['name'] == doc_payload['name']
    assert created_doc['identifier'] == doc_payload['identifier']
    assert created_doc['processing_status'] == 'IDLE'
    assert len(created_doc['history']) >= 1
    doc_id = created_doc['id']

    # 2. Leitura por ID (GET /doc/{id})
    response_get = client.get(
        f'/doc/{doc_id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response_get.status_code == HTTPStatus.OK
    doc_data = response_get.json()
    assert doc_data['id'] == doc_id
    assert doc_data['name'] == doc_payload['name']

    # 3. Listagem geral de documentos (GET /doc)
    response_list = client.get(
        '/doc',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response_list.status_code == HTTPStatus.OK
    docs_list = response_list.json()['documents']
    assert any(d['id'] == doc_id for d in docs_list)


@pytest.mark.asyncio
@patch('lumina.services.kanban_service.send_message', new_callable=AsyncMock)
async def test_characterization_kanban_flow(
    mock_send_message, client, token, session, user
):
    """
    Caracterização da transição de status do documento no Kanban e disparo de notificações.
    """
    # Cria auditor no banco para ser notificado
    auditor = User(
        username='auditor_teste',
        email='auditor@teste.com',
        password='hash',
        phone_number='5501988887777',
        access_level=AccessType.AUDITOR,
    )
    session.add(auditor)
    await session.commit()
    await session.refresh(auditor)

    # 1. Cria documento inicial
    doc_payload = {
        'name': 'Edital Kanban Flow',
        'identifier': f'KANBAN-{uuid4().hex[:6]}',
        'description': 'Descricao kanban',
        'typification_ids': None,
        'editors_ids': None,
    }
    response_create = client.post(
        '/doc',
        headers={'Authorization': f'Bearer {token}'},
        json=doc_payload,
    )
    assert response_create.status_code == HTTPStatus.CREATED
    doc_id = response_create.json()['id']

    # 2. Transição para UNDER_CONSTRUCTION
    resp_under_const = client.put(
        f'/doc/{doc_id}/status/under-construction',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp_under_const.status_code == HTTPStatus.OK
    history_statuses = [
        h['status'] for h in resp_under_const.json()['history']
    ]
    assert 'UNDER_CONSTRUCTION' in history_statuses

    # 3. Transição para WAITING_FOR_REVIEW (dispara notificação para auditores e criador)
    resp_waiting = client.put(
        f'/doc/{doc_id}/status/waiting-review',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp_waiting.status_code == HTTPStatus.OK
    history_statuses_waiting = [
        h['status'] for h in resp_waiting.json()['history']
    ]
    assert 'WAITING_FOR_REVIEW' in history_statuses_waiting
    assert mock_send_message.called

    # 4. Transição para COMPLETED
    resp_completed = client.put(
        f'/doc/{doc_id}/status/completed',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp_completed.status_code == HTTPStatus.OK
    history_statuses_completed = [
        h['status'] for h in resp_completed.json()['history']
    ]
    assert 'COMPLETED' in history_statuses_completed


@pytest.mark.asyncio
async def test_characterization_user_crud_flow(client, user, token):
    """
    Caracterização do CRUD de Usuários.
    """
    unique_suffix = uuid4().hex[:6]
    user_payload = {
        'username': f'carac_user_{unique_suffix}',
        'email': f'carac_{unique_suffix}@example.com',
        'phone_number': f'55119{unique_suffix[:8]}',
        'password': 'password123',
    }

    # 1. Criação (POST /user)
    response_create = client.post(
        '/user',
        headers={'Authorization': f'Bearer {token}'},
        json=user_payload,
    )
    assert response_create.status_code == HTTPStatus.CREATED
    created_user = response_create.json()
    assert created_user['username'] == user_payload['username']
    assert created_user['email'] == user_payload['email']

    # 2. Listagem (GET /user)
    response_list = client.get(
        '/user',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response_list.status_code == HTTPStatus.OK
    users = response_list.json()['users']
    assert any(u['id'] == created_user['id'] for u in users)

    # 3. Atualização do próprio usuário autenticado (PUT /user)
    update_payload = {
        'id': str(user.id),
        'username': f'updated_{unique_suffix}',
        'email': user.email,
        'phone_number': user.phone_number,
        'password': 'newpassword123',
    }
    response_update = client.put(
        '/user',
        headers={'Authorization': f'Bearer {token}'},
        json=update_payload,
    )
    assert response_update.status_code == HTTPStatus.OK
    assert response_update.json()['username'] == update_payload['username']


@pytest.mark.asyncio
async def test_characterization_stats_kpis_flow(client, token):
    """
    Caracterização das métricas gerais do sistema (GET /stats/kpis).
    """
    response = client.get(
        '/stats/kpis',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert 'total_users' in data
    assert 'total_documents' in data
    assert 'total_analyses' in data
    assert isinstance(data['total_users'], int)
    assert isinstance(data['total_documents'], int)
