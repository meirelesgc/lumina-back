"""Ações de usuário das jornadas. Cada uma confere o próprio status."""

from http import HTTPStatus
from itertools import count

_phones = count(1)
PASSWORD = 'senha-segura'


def sign_up(client, name: str) -> dict:
    response = client.post(
        '/user',
        json={
            'username': name,
            'email': f'{name}@lumina.com.br',
            'phone_number': f'5521988{next(_phones):06d}',
            'password': PASSWORD,
        },
    )
    assert response.status_code == HTTPStatus.CREATED, response.text
    return response.json()


def log_in(client, name: str) -> dict:
    """Entra como a pessoa e devolve os cabeçalhos da sessão dela."""
    response = client.post(
        '/auth/token',
        data={'username': f'{name}@lumina.com.br', 'password': PASSWORD},
    )
    assert response.status_code == HTTPStatus.OK, response.text
    return {'Authorization': f'Bearer {response.json()["access_token"]}'}


def create_group(client, headers, name: str, item_names: list[str]):
    group = client.post(
        '/document-group', headers=headers, json={'name': name}
    )
    assert group.status_code == HTTPStatus.CREATED, group.text
    items = []
    for item_name in item_names:
        item = client.post(
            f'/document-group/{group.json()["id"]}/item',
            headers=headers,
            json={'name': item_name},
        )
        assert item.status_code == HTTPStatus.CREATED, item.text
        items.append(item.json())
    return group.json(), items


def create_typification(client, headers, name: str) -> dict:
    response = client.post(
        '/typification',
        headers=headers,
        json={'name': name, 'source_ids': []},
    )
    assert response.status_code == HTTPStatus.CREATED, response.text
    return response.json()


def attach(client, headers, item_id, **payload) -> dict:
    response = client.post(
        f'/document-group/item/{item_id}/attachment',
        headers=headers,
        json=payload,
    )
    assert response.status_code == HTTPStatus.CREATED, response.text
    return response.json()


def create_project(client, headers, name: str, group_id) -> dict:
    response = client.post(
        '/project',
        headers=headers,
        json={'name': name, 'document_group_id': group_id},
    )
    assert response.status_code == HTTPStatus.CREATED, response.text
    return response.json()


def invite_advisee(client, advisor_headers, advisee_email: str) -> str:
    response = client.post(
        '/invitations', headers=advisor_headers, json={'email': advisee_email}
    )
    assert response.status_code == HTTPStatus.CREATED, response.text
    return response.json()['token']


def accept_invitation(client, advisee_headers, token: str) -> None:
    response = client.post(
        f'/invitations/{token}/accept', headers=advisee_headers
    )
    assert response.status_code == HTTPStatus.OK, response.text
