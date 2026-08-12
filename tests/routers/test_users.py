from http import HTTPStatus

from lumina.schemas import UserPublic


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


def test_read_users(client):
    response = client.get('/user')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'users': []}


def test_read_users_with_users(client, user):
    user_schema = UserPublic.model_validate(user).model_dump(mode='json')
    response = client.get('/user')
    assert response.json() == {'users': [user_schema]}


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
