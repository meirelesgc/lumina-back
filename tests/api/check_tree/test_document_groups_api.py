from http import HTTPStatus
import pytest

@pytest.mark.asyncio
async def test_create_group(client, token):
    response = client.post(
        '/document-group',
        headers={'Authorization': f'Bearer {token}'},
        json={'name': 'API Test Group'}
    )
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['name'] == 'API Test Group'

@pytest.mark.asyncio
async def test_read_groups(client, token):
    response = client.get(
        '/document-group',
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.OK
    assert 'groups' in response.json()
