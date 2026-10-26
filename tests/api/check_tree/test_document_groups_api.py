from http import HTTPStatus

import pytest


@pytest.mark.asyncio
async def test_create_group(client, token):
    response = client.post(
        '/document-group',
        headers={'Authorization': f'Bearer {token}'},
        json={'name': 'API Test Group'},
    )
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['name'] == 'API Test Group'


@pytest.mark.asyncio
async def test_read_groups(client, token):
    response = client.get(
        '/document-group', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.OK
    assert 'groups' in response.json()


def _auth(token):
    return {'Authorization': f'Bearer {token}'}


def _create_group_with_items(client, token, names):
    group = client.post(
        '/document-group', headers=_auth(token), json={'name': 'Grupo TCC'}
    ).json()
    items = [
        client.post(
            f'/document-group/{group["id"]}/item',
            headers=_auth(token),
            json={'name': name},
        ).json()
        for name in names
    ]
    return group, items


def test_new_item_goes_to_end_of_group(client, token):
    group, items = _create_group_with_items(
        client, token, ['Anteprojeto', 'TCC', 'Outro documento']
    )

    assert [item['position'] for item in items] == [1, 2, 3]

    by_id = client.get(f'/document-group/{group["id"]}', headers=_auth(token))
    listed = client.get(
        f'/document-group/{group["id"]}/items', headers=_auth(token)
    )
    all_groups = client.get(
        '/document-group', headers=_auth(token), params={'q': 'Grupo TCC'}
    )

    expected = ['Anteprojeto', 'TCC', 'Outro documento']
    assert [i['name'] for i in by_id.json()['items']] == expected
    assert [i['name'] for i in listed.json()] == expected
    assert [i['name'] for i in all_groups.json()['groups'][0]['items']] == (
        expected
    )


def test_deleted_item_is_not_listed(client, token):
    group, items = _create_group_with_items(
        client, token, ['Anteprojeto', 'TCC']
    )
    client.delete(
        f'/document-group/item/{items[0]["id"]}', headers=_auth(token)
    )

    by_id = client.get(f'/document-group/{group["id"]}', headers=_auth(token))
    listed = client.get(
        f'/document-group/{group["id"]}/items', headers=_auth(token)
    )

    assert [i['name'] for i in by_id.json()['items']] == ['TCC']
    assert [i['name'] for i in listed.json()] == ['TCC']


def test_reorder_items(client, token):
    group, items = _create_group_with_items(
        client, token, ['Anteprojeto', 'TCC', 'Outro documento']
    )
    anteprojeto, tcc, outro = (item['id'] for item in items)

    response = client.put(
        f'/document-group/{group["id"]}/items/order',
        headers=_auth(token),
        json={'item_ids': [tcc, anteprojeto, outro]},
    )

    assert response.status_code == HTTPStatus.OK
    assert [i['id'] for i in response.json()['items']] == [
        tcc,
        anteprojeto,
        outro,
    ]
    assert [i['position'] for i in response.json()['items']] == [1, 2, 3]
    listed = client.get(
        f'/document-group/{group["id"]}/items', headers=_auth(token)
    )
    assert [i['id'] for i in listed.json()] == [tcc, anteprojeto, outro]


@pytest.mark.parametrize(
    'make_ids',
    [
        lambda ids, deleted, foreign: [ids[1], ids[0]],
        lambda ids, deleted, foreign: [ids[1], ids[0], ids[2], ids[2]],
        lambda ids, deleted, foreign: [ids[1], ids[0], ids[2], deleted],
        lambda ids, deleted, foreign: [ids[1], ids[0], foreign],
    ],
    ids=['incompleta', 'repetida', 'item_excluido', 'item_de_outro_grupo'],
)
def test_reorder_items_rejects_invalid_list(client, token, make_ids):
    group, items = _create_group_with_items(
        client, token, ['Anteprojeto', 'TCC', 'Outro documento', 'Velho']
    )
    ids = [item['id'] for item in items[:3]]
    deleted = items[3]['id']
    client.delete(f'/document-group/item/{deleted}', headers=_auth(token))
    other = client.post(
        '/document-group', headers=_auth(token), json={'name': 'Outro grupo'}
    ).json()
    foreign = client.post(
        f'/document-group/{other["id"]}/item',
        headers=_auth(token),
        json={'name': 'Manuscrito'},
    ).json()['id']

    response = client.put(
        f'/document-group/{group["id"]}/items/order',
        headers=_auth(token),
        json={'item_ids': make_ids(ids, deleted, foreign)},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    listed = client.get(
        f'/document-group/{group["id"]}/items', headers=_auth(token)
    )
    assert [i['id'] for i in listed.json()] == ids


def test_reorder_items_of_missing_group(client, token):
    group, items = _create_group_with_items(client, token, ['Anteprojeto'])
    client.delete(f'/document-group/{group["id"]}', headers=_auth(token))

    response = client.put(
        f'/document-group/{group["id"]}/items/order',
        headers=_auth(token),
        json={'item_ids': [items[0]['id']]},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
