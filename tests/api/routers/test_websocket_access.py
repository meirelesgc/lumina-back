from http import HTTPStatus

import pytest
from starlette.websockets import WebSocketDisconnect


def test_websocket_sem_sessao_nao_conecta(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            '/ws/00000000-0000-0000-0000-000000000001'
        ):
            pass


def test_websocket_de_documento_sem_acesso_nao_conecta(
    client, token, other_token
):
    doc = client.post(
        '/doc',
        headers={'Authorization': f'Bearer {token}'},
        json={'name': 'Artigo', 'identifier': 'WS-1', 'description': 'x'},
    )
    assert doc.status_code == HTTPStatus.CREATED

    client.cookies.set('access_token', other_token)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f'/doc/message/{doc.json()["id"]}/ws'):
            pass
