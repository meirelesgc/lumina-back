from http import HTTPStatus
from uuid import uuid4

import pytest

from lumina.services.crossref_client import DoiMetadata

DOI = '10.1590/s0102-311x2023000100001'
ARTIGO = DoiMetadata(
    title='Saúde coletiva e pesquisa',
    authors=['Ana Souza', 'Bruno Lima'],
    year=2023,
    container_title='Cadernos de Saúde Pública',
)


def _auth(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def item(client, token):
    group = client.post(
        '/document-group', headers=_auth(token), json={'name': 'TCC'}
    ).json()
    return client.post(
        f'/document-group/{group["id"]}/item',
        headers=_auth(token),
        json={'name': 'Anteprojeto'},
    ).json()


def _typification(client, token, name='Artigo científico'):
    return client.post(
        '/typification',
        headers=_auth(token),
        json={'name': name, 'source_ids': []},
    ).json()


def _attach(client, token, item_id, **payload):
    return client.post(
        f'/document-group/item/{item_id}/attachment',
        headers=_auth(token),
        json=payload,
    )


def _list(client, token, item_id):
    return client.get(
        f'/document-group/item/{item_id}/attachments', headers=_auth(token)
    )


# Cadastro


def test_attach_to_missing_item(client, token, crossref):
    response = _attach(
        client, token, uuid4(), kind='LINK', title='Livro', url='https://a.b'
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_attach_to_deleted_item(client, token, item, crossref):
    client.delete(f'/document-group/item/{item["id"]}', headers=_auth(token))

    response = _attach(
        client,
        token,
        item['id'],
        kind='LINK',
        title='Livro',
        url='https://a.b',
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_description_is_kept_as_written(client, token, item, crossref):
    description = (
        'Leia os critérios da seção de metodologia antes de escrever o '
        'anteprojeto'
    )

    response = _attach(
        client,
        token,
        item['id'],
        kind='LINK',
        title='Livro XPTO',
        url='https://editora.example/xpto',
        description=description,
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['description'] == description
    assert _list(client, token, item['id']).json()[0]['description'] == (
        description
    )


def test_new_attachment_goes_to_end(client, token, item, crossref):
    first = _attach(
        client, token, item['id'], kind='LINK', title='A', url='https://a.b'
    ).json()
    second = _attach(
        client, token, item['id'], kind='LINK', title='B', url='https://b.c'
    ).json()

    assert (first['position'], second['position']) == (1, 2)
    assert [a['id'] for a in _list(client, token, item['id']).json()] == [
        first['id'],
        second['id'],
    ]


# Tipificação


def test_attach_typification(client, token, item, crossref):
    typification = _typification(client, token)

    response = _attach(
        client,
        token,
        item['id'],
        kind='TYPIFICATION',
        typification_id=typification['id'],
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['typification'] == {
        'id': typification['id'],
        'name': 'Artigo científico',
    }


def test_attach_missing_or_deleted_typification(client, token, item, crossref):
    deleted = _typification(client, token, name='Excluída')
    client.delete(f'/typification/{deleted["id"]}', headers=_auth(token))

    for payload in (
        {'typification_id': str(uuid4())},
        {'typification_id': deleted['id']},
        {},
    ):
        response = _attach(
            client, token, item['id'], kind='TYPIFICATION', **payload
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_attach_same_typification_twice(client, token, item, crossref):
    typification = _typification(client, token)
    _attach(
        client,
        token,
        item['id'],
        kind='TYPIFICATION',
        typification_id=typification['id'],
    )

    response = _attach(
        client,
        token,
        item['id'],
        kind='TYPIFICATION',
        typification_id=typification['id'],
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert len(_list(client, token, item['id']).json()) == 1


# DOI


def test_attach_doi_with_url_prefix(client, token, item, crossref):
    response = _attach(
        client,
        token,
        item['id'],
        kind='DOI',
        doi='https://doi.org/10.1590/S0102-311X2023000100001',
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['doi'] == DOI
    assert response.json()['doi_url'] == f'https://doi.org/{DOI}'
    assert crossref.calls == [DOI]


@pytest.mark.parametrize(
    'doi', ['abc', '11.1234/abc', '10.123/abc', '10.1234/', 'ftp://x/10.1/a']
)
def test_attach_invalid_doi(client, token, item, crossref, doi):
    response = _attach(client, token, item['id'], kind='DOI', doi=doi)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert crossref.calls == []


def test_attach_same_doi_written_differently(client, token, item, crossref):
    _attach(client, token, item['id'], kind='DOI', doi=DOI)

    response = _attach(
        client,
        token,
        item['id'],
        kind='DOI',
        doi='doi:10.1590/S0102-311X2023000100001',
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert len(_list(client, token, item['id']).json()) == 1


# Metadados do Crossref


def test_crossref_fills_metadata(client, token, item, crossref):
    crossref.works[DOI] = ARTIGO

    response = _attach(client, token, item['id'], kind='DOI', doi=DOI)

    body = response.json()
    assert body['title'] == 'Saúde coletiva e pesquisa'
    assert body['authors'] == ['Ana Souza', 'Bruno Lima']
    assert body['year'] == 2023
    assert body['container_title'] == 'Cadernos de Saúde Pública'
    assert body['metadata_source'] == 'CROSSREF'


def test_typed_title_wins_over_crossref(client, token, item, crossref):
    crossref.works[DOI] = ARTIGO

    response = _attach(
        client, token, item['id'], kind='DOI', doi=DOI, title='Artigo Z'
    )

    body = response.json()
    assert body['title'] == 'Artigo Z'
    assert body['authors'] == ['Ana Souza', 'Bruno Lima']
    assert body['year'] == 2023
    assert body['container_title'] == 'Cadernos de Saúde Pública'


@pytest.mark.parametrize('title', ['Artigo Z', None])
def test_crossref_unavailable_still_saves(
    client, token, item, crossref, title
):
    response = _attach(
        client, token, item['id'], kind='DOI', doi=DOI, title=title
    )

    assert response.status_code == HTTPStatus.CREATED
    body = response.json()
    assert body['title'] == title
    assert body['authors'] == []
    assert body['year'] is None
    assert body['container_title'] is None
    assert body['metadata_source'] == 'MANUAL'


def test_editing_description_does_not_query_crossref(
    client, token, item, crossref
):
    crossref.works[DOI] = ARTIGO
    created = _attach(client, token, item['id'], kind='DOI', doi=DOI).json()
    crossref.works[DOI] = DoiMetadata('Outro', [], None, None)

    response = client.put(
        '/document-group/attachment',
        headers=_auth(token),
        json={
            'id': created['id'],
            'kind': 'DOI',
            'doi': 'https://doi.org/10.1590/S0102-311X2023000100001',
            'description': 'Leia a introdução',
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert crossref.calls == [DOI]
    body = response.json()
    assert body['description'] == 'Leia a introdução'
    assert body['title'] == 'Saúde coletiva e pesquisa'
    assert body['metadata_source'] == 'CROSSREF'


def test_changing_doi_queries_crossref_again(client, token, item, crossref):
    created = _attach(client, token, item['id'], kind='DOI', doi=DOI).json()
    crossref.works['10.1234/novo'] = ARTIGO

    response = client.put(
        '/document-group/attachment',
        headers=_auth(token),
        json={'id': created['id'], 'kind': 'DOI', 'doi': '10.1234/NOVO'},
    )

    assert response.status_code == HTTPStatus.OK
    assert crossref.calls == [DOI, '10.1234/novo']
    assert response.json()['doi'] == '10.1234/novo'
    assert response.json()['title'] == 'Saúde coletiva e pesquisa'
    assert response.json()['metadata_source'] == 'CROSSREF'


# Link


def test_attach_link(client, token, item, crossref):
    response = _attach(
        client,
        token,
        item['id'],
        kind='LINK',
        title='Livro XPTO',
        url='https://editora.example/xpto',
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['title'] == 'Livro XPTO'
    assert response.json()['url'] == 'https://editora.example/xpto'


@pytest.mark.parametrize(
    ('title', 'url'),
    [
        ('', 'https://editora.example/xpto'),
        ('   ', 'https://editora.example/xpto'),
        (None, 'https://editora.example/xpto'),
        ('Livro', 'ftp://editora.example/xpto'),
        ('Livro', 'javascript:alert(1)'),
        ('Livro', None),
    ],
)
def test_attach_invalid_link(client, token, item, crossref, title, url):
    response = _attach(
        client, token, item['id'], kind='LINK', title=title, url=url
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_attach_same_url_twice(client, token, item, crossref):
    url = 'https://editora.example/xpto'
    _attach(client, token, item['id'], kind='LINK', title='A', url=url)

    response = _attach(
        client, token, item['id'], kind='LINK', title='B', url=url
    )

    assert response.status_code == HTTPStatus.CONFLICT


# Listar, editar, reordenar e excluir


def test_list_attachments_of_missing_item(client, token, crossref):
    response = _list(client, token, uuid4())

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_reorder_attachments(client, token, item, crossref):
    ids = [
        _attach(
            client, token, item['id'], kind='LINK', title=n, url=f'https://{n}'
        ).json()['id']
        for n in ('a.b', 'c.d', 'e.f')
    ]

    response = client.put(
        f'/document-group/item/{item["id"]}/attachments/order',
        headers=_auth(token),
        json={'attachment_ids': [ids[2], ids[0], ids[1]]},
    )

    assert response.status_code == HTTPStatus.OK
    assert [a['id'] for a in response.json()] == [ids[2], ids[0], ids[1]]
    assert [a['id'] for a in _list(client, token, item['id']).json()] == [
        ids[2],
        ids[0],
        ids[1],
    ]


@pytest.mark.parametrize(
    'make_ids',
    [
        lambda ids, foreign: [ids[1], ids[0]],
        lambda ids, foreign: [ids[1], ids[0], ids[2], ids[2]],
        lambda ids, foreign: [ids[1], ids[0], ids[2], foreign],
    ],
    ids=['incompleta', 'repetida', 'de_outro_item'],
)
def test_reorder_attachments_rejects_invalid_list(
    client, token, item, crossref, make_ids
):
    ids = [
        _attach(
            client, token, item['id'], kind='LINK', title=n, url=f'https://{n}'
        ).json()['id']
        for n in ('a.b', 'c.d', 'e.f')
    ]
    other_item = client.post(
        f'/document-group/{item["group_id"]}/item',
        headers=_auth(token),
        json={'name': 'TCC'},
    ).json()
    foreign = _attach(
        client,
        token,
        other_item['id'],
        kind='LINK',
        title='x',
        url='https://x',
    ).json()['id']

    response = client.put(
        f'/document-group/item/{item["id"]}/attachments/order',
        headers=_auth(token),
        json={'attachment_ids': make_ids(ids, foreign)},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert [a['id'] for a in _list(client, token, item['id']).json()] == ids


def test_kind_cannot_change(client, token, item, crossref):
    created = _attach(
        client, token, item['id'], kind='LINK', title='A', url='https://a.b'
    ).json()

    response = client.put(
        '/document-group/attachment',
        headers=_auth(token),
        json={'id': created['id'], 'kind': 'DOI', 'doi': DOI},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert _list(client, token, item['id']).json()[0]['kind'] == 'LINK'


def test_edit_link(client, token, item, crossref):
    created = _attach(
        client, token, item['id'], kind='LINK', title='A', url='https://a.b'
    ).json()

    response = client.put(
        '/document-group/attachment',
        headers=_auth(token),
        json={
            'id': created['id'],
            'kind': 'LINK',
            'title': 'Livro XPTO',
            'url': 'https://editora.example/xpto',
            'description': 'Capítulo 2',
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['title'] == 'Livro XPTO'
    assert response.json()['url'] == 'https://editora.example/xpto'
    assert response.json()['description'] == 'Capítulo 2'


def test_delete_attachment(client, token, item, crossref):
    created = _attach(
        client, token, item['id'], kind='LINK', title='A', url='https://a.b'
    ).json()

    response = client.delete(
        f'/document-group/attachment/{created["id"]}', headers=_auth(token)
    )

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert _list(client, token, item['id']).json() == []


def test_deleted_attachment_frees_its_url(client, token, item, crossref):
    created = _attach(
        client, token, item['id'], kind='LINK', title='A', url='https://a.b'
    ).json()
    client.delete(
        f'/document-group/attachment/{created["id"]}', headers=_auth(token)
    )

    response = _attach(
        client, token, item['id'], kind='LINK', title='A', url='https://a.b'
    )

    assert response.status_code == HTTPStatus.CREATED


# Tipificação excluída


def test_deleted_typification_hides_attachment(client, token, item, crossref):
    typification = _typification(client, token)
    _attach(
        client,
        token,
        item['id'],
        kind='TYPIFICATION',
        typification_id=typification['id'],
    )
    _attach(
        client, token, item['id'], kind='LINK', title='A', url='https://a.b'
    )

    response = client.delete(
        f'/typification/{typification["id"]}', headers=_auth(token)
    )

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert [a['kind'] for a in _list(client, token, item['id']).json()] == [
        'LINK'
    ]


def test_attachment_of_deleted_item_is_gone(client, token, item, crossref):
    created = _attach(
        client, token, item['id'], kind='LINK', title='A', url='https://a.b'
    ).json()
    client.delete(f'/document-group/item/{item["id"]}', headers=_auth(token))

    edited = client.put(
        '/document-group/attachment',
        headers=_auth(token),
        json={
            'id': created['id'],
            'kind': 'LINK',
            'title': 'B',
            'url': 'https://a.b',
        },
    )
    deleted = client.delete(
        f'/document-group/attachment/{created["id"]}', headers=_auth(token)
    )

    assert edited.status_code == HTTPStatus.NOT_FOUND
    assert deleted.status_code == HTTPStatus.NOT_FOUND
