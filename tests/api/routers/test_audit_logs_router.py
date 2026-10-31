from http import HTTPStatus

import pytest

from lumina.schemas import AccessType


def test_visitante_nao_le_a_auditoria(client):
    response = client.get('/audit-log')
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert 'audit_logs' not in response.json()


def test_usuario_comum_nao_le_a_auditoria(client, token):
    response = client.get(
        '/audit-log', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'audit_logs' not in response.json()


@pytest.mark.asyncio
async def test_admin_le_a_auditoria(client, session, user, token):
    user.access_level = AccessType.ADMIN
    await session.commit()

    response = client.get(
        '/audit-log', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.OK
    assert any(
        log['action'] == 'LOGIN' for log in response.json()['audit_logs']
    )
