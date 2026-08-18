"""
Template: Teste de API (Router / Endpoint)

Foco: Fluxo de ponta a ponta (Cliente até o Banco), e HTTP status codes.
"""

from http import HTTPStatus


def test_get_resource_success(client, token):
    """
    Jornada de Sucesso: Requisitando recurso com Autenticação correta.
    """
    response = client.get(
        '/unit',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.OK
    assert 'units' in response.json()


def test_get_resource_unauthorized(client):
    """
    Testes de Segurança/Transversais: Cenário sem token.
    """
    response = client.get('/unit')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_create_resource_invalid_payload(client, token):
    """
    Erros previstos (400 / 422).
    """
    response = client.post(
        '/unit',
        headers={'Authorization': f'Bearer {token}'},
        json={'name': ''},  # Nome vazio violando schema
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
