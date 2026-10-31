from http import HTTPStatus
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

from lumina.core.security import get_password_hash
from lumina.models import AccessType
from tests.conftest import UserFactory

pytestmark = pytest.mark.usefixtures('user_is_admin')


def _auth(token):
    return {'Authorization': f'Bearer {token}'}


def _login(client, user):
    response = client.post(
        '/auth/token',
        data={'username': user.email, 'password': user.clean_password},
    )
    return response.json()['access_token']


async def _create_user(session, **fields):
    user = UserFactory(password=get_password_hash('testtest'), **fields)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    user.clean_password = 'testtest'
    return user


@pytest_asyncio.fixture
async def advisor(session):
    return await _create_user(session, access_level=AccessType.ADMIN)


@pytest_asyncio.fixture
async def admin(session):
    return await _create_user(session, access_level=AccessType.ADMIN)


@pytest.fixture
def guide(client, token, crossref):
    """Grupo TCC com três itens e quatro anexos, e um projeto do dono."""
    group = client.post(
        '/document-group', headers=_auth(token), json={'name': 'TCC'}
    ).json()
    items = {
        name: client.post(
            f'/document-group/{group["id"]}/item',
            headers=_auth(token),
            json={'name': name},
        ).json()
        for name in ('Anteprojeto', 'TCC', 'Outro documento')
    }
    typification = client.post(
        '/typification',
        headers=_auth(token),
        json={'name': 'Artigo científico', 'source_ids': []},
    ).json()

    def attach(item, **payload):
        return client.post(
            f'/document-group/item/{items[item]["id"]}/attachment',
            headers=_auth(token),
            json=payload,
        ).json()

    attachments = {
        'tipificacao': attach(
            'Anteprojeto',
            kind='TYPIFICATION',
            typification_id=typification['id'],
            description='Leia os critérios de metodologia',
        ),
        'artigo': attach('TCC', kind='DOI', doi='10.1234/artigo'),
        'livro': attach(
            'Outro documento',
            kind='LINK',
            title='Livro XPTO',
            url='https://editora.example/xpto',
        ),
        'manual': attach(
            'Outro documento',
            kind='LINK',
            title='Manual',
            url='https://editora.example/manual',
        ),
    }
    project = client.post(
        '/project',
        headers=_auth(token),
        json={'name': 'Meu TCC', 'document_group_id': group['id']},
    ).json()
    return {
        'group': group,
        'items': items,
        'typification': typification,
        'attachments': attachments,
        'project': project,
    }


def _read(client, token, project_id):
    return client.get(
        f'/project/{project_id}/study-guide', headers=_auth(token)
    )


def _studied(client, token, project_id, attachment_id, method='put'):
    return client.request(
        method.upper(),
        f'/project/{project_id}/study-guide/attachment/{attachment_id}/studied',
        headers=_auth(token),
    )


def _attachment(body, attachment_id):
    return next(
        attachment
        for item in body['items']
        for attachment in item['attachments']
        if attachment['id'] == attachment_id
    )


def _link_advisor(client, advisor, advisee_token, advisee):
    invitation = client.post(
        '/invitations',
        headers=_auth(_login(client, advisor)),
        json={'email': advisee.email},
    ).json()
    response = client.post(
        f'/invitations/{invitation["token"]}/accept',
        headers=_auth(advisee_token),
    )
    assert response.status_code == HTTPStatus.OK


# Guia de estudo do projeto


def test_owner_reads_guide_in_order(client, token, guide):
    response = _read(client, token, guide['project']['id'])

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body['document_group'] == {
        'id': guide['group']['id'],
        'name': 'TCC',
    }
    assert [item['name'] for item in body['items']] == [
        'Anteprojeto',
        'TCC',
        'Outro documento',
    ]
    assert [
        [a['kind'] for a in item['attachments']] for item in body['items']
    ] == [['TYPIFICATION'], ['DOI'], ['LINK', 'LINK']]
    tipificacao = body['items'][0]['attachments'][0]
    assert tipificacao['description'] == 'Leia os critérios de metodologia'
    assert tipificacao['typification']['name'] == 'Artigo científico'
    assert body['items'][1]['attachments'][0]['doi_url'] == (
        'https://doi.org/10.1234/artigo'
    )
    assert tipificacao['studied'] is False
    assert tipificacao['studied_at'] is None
    assert (body['total_attachments'], body['studied_attachments']) == (4, 0)


def test_guide_of_project_without_group(client, token):
    project = client.post(
        '/project', headers=_auth(token), json={'name': 'Sem grupo'}
    ).json()

    response = _read(client, token, project['id'])

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'project_id': project['id'],
        'document_group': None,
        'items': [],
        'total_attachments': 0,
        'studied_attachments': 0,
    }


def test_advisor_and_admin_read_guide(
    client, token, user, guide, advisor, admin
):
    _link_advisor(client, advisor, token, user)
    _studied(
        client,
        token,
        guide['project']['id'],
        guide['attachments']['artigo']['id'],
    )
    owner_view = _read(client, token, guide['project']['id']).json()

    for reader in (advisor, admin):
        response = _read(
            client, _login(client, reader), guide['project']['id']
        )

        assert response.status_code == HTTPStatus.OK
        assert response.json() == owner_view


def test_outsider_cannot_read_guide(client, guide, other_user):
    response = _read(
        client, _login(client, other_user), guide['project']['id']
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_guide_of_missing_or_deleted_project(client, token, guide):
    assert _read(client, token, uuid4()).status_code == HTTPStatus.NOT_FOUND

    client.delete(f'/project/{guide["project"]["id"]}', headers=_auth(token))

    response = _read(client, token, guide['project']['id'])
    assert response.status_code == HTTPStatus.NOT_FOUND


# Marcar anexo como estudado


def test_owner_marks_attachment(client, token, guide):
    artigo = guide['attachments']['artigo']['id']

    response = _studied(client, token, guide['project']['id'], artigo)

    assert response.status_code == HTTPStatus.OK
    body = _read(client, token, guide['project']['id']).json()
    assert _attachment(body, artigo)['studied'] is True
    assert _attachment(body, artigo)['studied_at'] is not None
    assert body['studied_attachments'] == 1


@pytest.mark.asyncio
async def test_marking_twice_keeps_first_date(client, token, guide, session):
    project_id = guide['project']['id']
    artigo = guide['attachments']['artigo']['id']
    _studied(client, token, project_id, artigo)
    # O teste roda numa transação só, em que now() não muda. A data da
    # primeira marcação vai para trás para que uma regravação apareça.
    await session.execute(
        text("UPDATE study_progress SET studied_at = '2026-01-01T10:00:00'")
    )
    await session.commit()

    response = _studied(client, token, project_id, artigo)

    assert response.status_code == HTTPStatus.OK
    body = _read(client, token, project_id).json()
    assert _attachment(body, artigo)['studied_at'] == '2026-01-01T10:00:00'
    assert body['studied_attachments'] == 1


def test_unmark_attachment(client, token, guide):
    project_id = guide['project']['id']
    artigo = guide['attachments']['artigo']['id']
    _studied(client, token, project_id, artigo)

    response = _studied(client, token, project_id, artigo, method='delete')
    again = _studied(client, token, project_id, artigo, method='delete')

    assert response.status_code == HTTPStatus.OK
    assert again.status_code == HTTPStatus.OK
    body = _read(client, token, project_id).json()
    assert _attachment(body, artigo)['studied'] is False
    assert body['studied_attachments'] == 0


def test_advisor_and_admin_cannot_mark(
    client, token, user, guide, advisor, admin
):
    _link_advisor(client, advisor, token, user)
    artigo = guide['attachments']['artigo']['id']

    for reader in (advisor, admin):
        reader_token = _login(client, reader)
        for method in ('put', 'delete'):
            response = _studied(
                client, reader_token, guide['project']['id'], artigo, method
            )
            assert response.status_code == HTTPStatus.FORBIDDEN

    assert (
        _read(client, token, guide['project']['id']).json()[
            'studied_attachments'
        ]
        == 0
    )


def test_outsider_cannot_mark(client, guide, other_user):
    response = _studied(
        client,
        _login(client, other_user),
        guide['project']['id'],
        guide['attachments']['artigo']['id'],
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_mark_attachment_outside_project_group(client, token, guide):
    other = client.post(
        '/document-group', headers=_auth(token), json={'name': 'Artigo'}
    ).json()
    other_item = client.post(
        f'/document-group/{other["id"]}/item',
        headers=_auth(token),
        json={'name': 'Manuscrito'},
    ).json()
    foreign = client.post(
        f'/document-group/item/{other_item["id"]}/attachment',
        headers=_auth(token),
        json={'kind': 'LINK', 'title': 'x', 'url': 'https://x.y'},
    ).json()
    deleted = guide['attachments']['manual']['id']
    client.delete(
        f'/document-group/attachment/{deleted}', headers=_auth(token)
    )

    for attachment_id in (foreign['id'], deleted, str(uuid4())):
        response = _studied(
            client, token, guide['project']['id'], attachment_id
        )
        assert response.status_code == HTTPStatus.NOT_FOUND


def test_progress_is_kept_per_project(client, token, guide):
    second = client.post(
        '/project',
        headers=_auth(token),
        json={
            'name': 'Segundo TCC',
            'document_group_id': guide['group']['id'],
        },
    ).json()
    artigo = guide['attachments']['artigo']['id']

    _studied(client, token, guide['project']['id'], artigo)

    body = _read(client, token, second['id']).json()
    assert _attachment(body, artigo)['studied'] is False
    assert body['studied_attachments'] == 0


# Exclusões depois da marcação


def test_deleted_typification_leaves_guide_and_progress(client, token, guide):
    project_id = guide['project']['id']
    tipificacao = guide['attachments']['tipificacao']['id']
    _studied(client, token, project_id, tipificacao)

    client.delete(
        f'/typification/{guide["typification"]["id"]}', headers=_auth(token)
    )

    body = _read(client, token, project_id).json()
    assert body['items'][0]['attachments'] == []
    assert (body['total_attachments'], body['studied_attachments']) == (3, 0)
    response = _studied(client, token, project_id, tipificacao)
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_deleted_attachment_leaves_guide_and_progress(client, token, guide):
    project_id = guide['project']['id']
    livro = guide['attachments']['livro']['id']
    _studied(client, token, project_id, livro)
    _studied(client, token, project_id, guide['attachments']['artigo']['id'])

    client.delete(f'/document-group/attachment/{livro}', headers=_auth(token))

    body = _read(client, token, project_id).json()
    assert [a['title'] for a in body['items'][2]['attachments']] == ['Manual']
    assert (body['total_attachments'], body['studied_attachments']) == (3, 1)


def test_deleted_item_leaves_guide(client, token, guide):
    project_id = guide['project']['id']
    client.delete(
        f'/document-group/item/{guide["items"]["TCC"]["id"]}',
        headers=_auth(token),
    )

    body = _read(client, token, project_id).json()
    assert [item['name'] for item in body['items']] == [
        'Anteprojeto',
        'Outro documento',
    ]
    assert body['total_attachments'] == 3
    response = _studied(
        client, token, project_id, guide['attachments']['artigo']['id']
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
