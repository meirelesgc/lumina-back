from datetime import datetime
from http import HTTPStatus
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from lumina.models import Document, Project


def auth(token):
    return {'Authorization': f'Bearer {token}'}


def create_doc(client, token, identifier='ED-1'):
    response = client.post(
        '/doc',
        headers=auth(token),
        json={
            'name': f'Edital {identifier}',
            'identifier': identifier,
            'description': 'Edital de teste',
        },
    )
    assert response.status_code == HTTPStatus.CREATED, response.text
    return response.json()


def test_documento_nao_traz_historico(client, token):
    doc = create_doc(client, token)

    response = client.get(f'/doc/{doc["id"]}', headers=auth(token))

    assert response.status_code == HTTPStatus.OK
    assert 'history' not in response.json()


@patch('lumina.routers.docs.releases.release_pipeline', new_callable=AsyncMock)
def test_release_enviado_aparece_so_no_proprio_documento(
    _pipeline, client, token
):
    doc = create_doc(client, token, 'ED-1')
    other = create_doc(client, token, 'ED-2')

    response = client.post(
        f'/doc/{doc["id"]}/release',
        headers=auth(token),
        files={'file': ('artigo.pdf', b'%PDF-1.4', 'application/pdf')},
    )
    assert response.status_code == HTTPStatus.CREATED, response.text
    release = response.json()
    assert 'history_id' not in release

    listed = client.get(
        f'/doc/{doc["id"]}/release', headers=auth(token)
    ).json()['releases']
    assert [item['id'] for item in listed] == [release['id']]

    assert (
        client.get(f'/doc/{other["id"]}/release', headers=auth(token)).json()[
            'releases'
        ]
        == []
    )


@pytest.mark.asyncio
async def test_lista_documentos_do_mais_antigo_ao_mais_recente(
    client, session, token
):
    recent = create_doc(client, token, 'ED-RECENTE')
    old = create_doc(client, token, 'ED-ANTIGO')
    db_doc = await session.get(Document, UUID(old['id']))
    db_doc.created_at = datetime(2020, 1, 1)
    await session.commit()

    response = client.get('/doc', headers=auth(token))

    assert [doc['id'] for doc in response.json()['documents']] == [
        old['id'],
        recent['id'],
    ]


def test_rota_de_status_nao_existe(client, token):
    doc = create_doc(client, token)

    response = client.put(
        f'/doc/{doc["id"]}/status/completed', headers=auth(token)
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_documento_de_projeto_nao_traz_status(
    client, session, user, token
):
    project = Project(name='Projeto TCC', description='Descrição')
    project.set_creation_audit(user.id)
    session.add(project)
    await session.commit()

    response = client.post(
        '/project-document',
        headers=auth(token),
        json={
            'project_id': str(project.id),
            'name': 'Artigo',
            'status': 'PENDING',
        },
    )

    assert response.status_code == HTTPStatus.CREATED, response.text
    assert not {'status', 'sent_to_kanban'} & response.json().keys()
