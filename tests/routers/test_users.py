from http import HTTPStatus

import pytest
import pytest_asyncio

from lumina.schemas import AccessType, UserPublic


@pytest_asyncio.fixture
async def admin(session, user):
    user.access_level = AccessType.ADMIN
    await session.commit()
    return user


def test_create_user(client):
    response = client.post(
        '/user',
        json={
            'username': 'alice',
            'email': 'alice@example.com',
            'phone_number': '5501999999999',
            'password': 'secret',
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    assert 'id' in response.json()
    assert response.json()['username'] == 'alice'
    assert response.json()['email'] == 'alice@example.com'
    assert response.json()['phone_number'] == '5501999999999'


def test_visitante_nao_se_cadastra_como_admin(client):
    response = client.post(
        '/user',
        json={
            'username': 'mallory',
            'email': 'mallory@example.com',
            'phone_number': '5501966666666',
            'password': 'secret',
            'access_level': 'ADMIN',
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['access_level'] == AccessType.DEFAULT


def test_visitante_se_cadastra_como_default(client):
    response = client.post(
        '/user',
        json={
            'username': 'carol',
            'email': 'carol@example.com',
            'phone_number': '5501955555555',
            'password': 'secret',
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['access_level'] == AccessType.DEFAULT


@pytest.mark.asyncio
async def test_admin_promove_outra_conta(client, admin, other_user, token):
    response = client.put(
        '/user',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'id': str(other_user.id),
            'username': other_user.username,
            'email': other_user.email,
            'phone_number': other_user.phone_number,
            'access_level': 'ADMIN',
        },
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['access_level'] == AccessType.ADMIN


@pytest.mark.asyncio
async def test_admin_nao_usa_nivel_removido(client, admin, other_user, token):
    response = client.put(
        '/user',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'id': str(other_user.id),
            'username': other_user.username,
            'email': other_user.email,
            'phone_number': other_user.phone_number,
            'access_level': 'AUDITOR',
        },
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_token_de_usuario_removido_nao_vale(
    client, session, user, token
):
    user.set_deletion_audit(user.id)
    await session.commit()

    response = client.get(
        '/user/my', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_usuario_comum_nao_lista_usuarios(client, token):
    response = client.get(
        '/user', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_usuario_comum_nao_le_outra_conta(client, other_user, token):
    response = client.get(
        f'/user/{other_user.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_admin_lista_usuarios(client, admin, token):
    response = client.get(
        '/user', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()['users']) >= 1


@pytest.mark.asyncio
async def test_atualizacao_sem_nivel_mantem_admin(client, admin, token):
    response = client.put(
        '/user',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'id': str(admin.id),
            'username': admin.username,
            'email': admin.email,
            'phone_number': admin.phone_number,
        },
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['access_level'] == AccessType.ADMIN


def test_read_users_unauthorized(client):
    response = client.get('/user')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_read_users(client, admin, token):
    response = client.get('/user', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()['users']) >= 1


@pytest.mark.asyncio
async def test_read_users_with_users(client, admin, user, token):
    user_schema = UserPublic.model_validate(user).model_dump(mode='json')
    response = client.get('/user', headers={'Authorization': f'Bearer {token}'})
    assert any(u['id'] == user_schema['id'] for u in response.json()['users'])


def test_update_user(client, user, token):
    response = client.put(
        '/user',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'id': str(user.id),
            'username': 'bob',
            'email': 'bob@example.com',
            'phone_number': '5501988888888',
            'password': 'mynewpassword',
        },
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['username'] == 'bob'
    assert response.json()['email'] == 'bob@example.com'
    assert response.json()['phone_number'] == '5501988888888'
    assert response.json()['id'] == str(user.id)


def test_update_integrity_error(client, user, token):
    client.post(
        '/user',
        json={
            'username': 'bob',
            'email': 'fausto@example.com',
            'phone_number': '5501977777777',
            'password': 'secret',
        },
    )

    response_update = client.put(
        '/user',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'id': str(user.id),
            'username': 'fausto',
            'email': 'fausto@example.com',
            'phone_number': '5501988888888',
            'password': 'mynewpassword',
        },
    )

    assert response_update.status_code == HTTPStatus.CONFLICT
    assert response_update.json() == {
        'detail': 'Email or phone number already registered'
    }


def test_delete_user(client, user, token):
    response = client.delete(
        f'/user/{str(user.id)}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.asyncio
async def test_usuario_comum_nao_remove_outra_conta(
    client, session, other_user, token
):
    response = client.delete(
        f'/user/{other_user.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN

    await session.refresh(other_user)
    assert other_user.deleted_at is None


@pytest.mark.asyncio
async def test_admin_remove_outra_conta(client, admin, other_user, token):
    response = client.delete(
        f'/user/{other_user.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT

    users = client.get(
        '/user', headers={'Authorization': f'Bearer {token}'}
    ).json()['users']
    assert all(u['id'] != str(other_user.id) for u in users)


def test_update_user_with_wrong_user(client, other_user, token):
    response = client.put(
        '/user',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'id': str(other_user.id),
            'username': 'bob',
            'email': 'bob@example.com',
            'phone_number': '5501988888888',
            'password': 'mynewpassword',
        },
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {
        'detail': 'You are not authorized to update this user'
    }
