"""
Template de Teste de Caracterização para FastAPI (Lumina Back)
Use este arquivo como ponto de partida ao iniciar uma grande refatoração.
"""

from http import HTTPStatus
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_characterization_flow_example(client, token):
    """
    Fotografia do comportamento do fluxo afetado antes da refatoração.
    Valida status codes, formato do payload e contratos da API.
    """
    # 1. Arrange: Dados de entrada realistas
    payload = {
        'name': f'Item Caracterizacao {uuid4().hex[:6]}',
        'description': 'Descricao de teste para fotografia de comportamento',
    }

    # 2. Act: Execução da rota HTTP
    response = client.post(
        '/endpoint-do-fluxo',
        headers={'Authorization': f'Bearer {token}'},
        json=payload,
    )

    # 3. Assert: Validações observáveis (comportamento externo)
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert 'id' in data
    assert data['name'] == payload['name']


@pytest.mark.asyncio
@patch('lumina.workers.utils.send_message', new_callable=AsyncMock)
async def test_characterization_with_events(mock_send_message, client, token):
    """
    Fotografia de fluxos que geram efeitos colaterais (notificações, filas, workers).
    """
    response = client.put(
        '/endpoint-com-evento',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.OK
    assert mock_send_message.called
