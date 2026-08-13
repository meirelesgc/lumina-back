from http import HTTPStatus

import pytest


@pytest.mark.asyncio
async def test_create_unit(client, token):
    response = client.post(
        '/unit',
        headers={'Authorization': f'Bearer {token}'},
        json={'name': 'API Unit', 'location': 'API Location'},
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert 'id' in data
    assert data['name'] == 'API Unit'
    assert data['location'] == 'API Location'


@pytest.mark.asyncio
async def test_create_unit_conflict(client, token, unit):
    # Try to create a unit with the same name as the existing 'unit' fixture
    response = client.post(
        '/unit',
        headers={'Authorization': f'Bearer {token}'},
        json={'name': unit.name, 'location': 'Different Location'},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Unit name already exists'}


@pytest.mark.asyncio
async def test_read_units(client, token, unit):
    response = client.get(
        '/unit', headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert 'units' in data
    assert len(data['units']) >= 1
    assert any(u['id'] == str(unit.id) for u in data['units'])


@pytest.mark.asyncio
async def test_read_unit_by_id(client, token, unit):
    response = client.get(
        f'/unit/{unit.id}', headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(unit.id)
    assert data['name'] == unit.name


@pytest.mark.asyncio
async def test_read_unit_not_found(client, token):
    from uuid import uuid4

    response = client.get(
        f'/unit/{uuid4()}', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_update_unit(client, token, unit):
    response = client.put(
        '/unit',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'id': str(unit.id),
            'name': 'Updated Unit Name',
            'location': 'Updated Location',
        },
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['name'] == 'Updated Unit Name'
    assert data['location'] == 'Updated Location'


@pytest.mark.asyncio
async def test_delete_unit(client, token, unit):
    response = client.delete(
        f'/unit/{unit.id}', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.NO_CONTENT

    # Verify it was deleted (soft delete if that's the logic, or actually missing)
    check = client.get(
        f'/unit/{unit.id}', headers={'Authorization': f'Bearer {token}'}
    )
    assert check.status_code == HTTPStatus.NOT_FOUND


def test_unauthorized_access(client):
    response = client.post('/unit', json={'name': 'Test'})
    assert response.status_code == HTTPStatus.UNAUTHORIZED
