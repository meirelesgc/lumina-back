import uuid
from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_create_document_ai_message_endpoint(client, user, token):
    """
    Testa se o endpoint de IA retorna um JSON estruturado com 'answer' e 'citations'
    como parte do conteúdo string.
    """
    doc_id = str(uuid.uuid4())

    # Payload de resposta do AI Service simulado
    mock_ai_response = {
        'answer': 'Sim, a matriz GUT foi aplicada no item 3.',
        'references': [
            {
                'chunk_id': 'chunk_1',
                'text_snippet': 'item 3',
                'page': 1,
                'rects': [{'x1': 10.0, 'y1': 20.0, 'x2': 30.0, 'y2': 40.0}],
            }
        ],
    }

    # Precisamos mocar a verificação de permissão ou a lógica de DB para o documento
    # Como não temos fábrica de documentos aqui prontamente garantida,
    # vamos mocar a camada de serviço.

    with patch(
        'lumina.routers.docs.messages.message_service.create_message',
        new_callable=AsyncMock,
    ) as mock_create_msg:
        with patch(
            'lumina.routers.docs.messages.message_service.list_messages',
            new_callable=AsyncMock,
        ) as mock_list_msg:
            with patch(
                'lumina.routers.docs.messages.ai_service.create_ai_response',
                new_callable=AsyncMock,
            ) as mock_create_ai:
                # Setup do mock
                mock_list_msg.return_value = []
                mock_create_ai.return_value = mock_ai_response
                # O create_message retorna o schema salvo. Vamos simular algo.
                from datetime import datetime

                from lumina.schemas import DocumentMessagePublic

                # Mock create_message behavior
                def fake_create_message(*args, **kwargs):
                    msg_create = (
                        args[3]
                        if len(args) > 3
                        else kwargs.get('msg') or kwargs.get('data')
                    )
                    return DocumentMessagePublic(
                        id=uuid.uuid4(),
                        content=msg_create.content,
                        mentions=msg_create.mentions,
                        quoted_message=msg_create.quoted_message,
                        references=msg_create.references,
                        author=None,
                        document_id=uuid.UUID(doc_id),
                        release_id=uuid.uuid4(),
                        created_at=datetime.now(),
                    )

                mock_create_msg.side_effect = fake_create_message

                response = client.post(
                    f'/doc/{doc_id}/message/ai',
                    headers={'Authorization': f'Bearer {token}'},
                    json={'content': 'Onde a matriz foi aplicada?'},
                )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert 'content' in data
    assert 'references' in data

    # O content é a string da resposta
    assert data['content'] == 'Sim, a matriz GUT foi aplicada no item 3.'
    assert len(data['references']) == 1
    assert data['references'][0]['chunk_id'] == 'chunk_1'
    assert data['references'][0]['rects'][0]['x1'] == 10.0
