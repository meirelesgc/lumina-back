from http import HTTPStatus
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
import pytest_asyncio

from lumina.models import (
    Advisorship,
    DocumentMessage,
    DocumentRelease,
    Project,
    ProjectDocument,
)


def auth(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def doc(client, token):
    response = client.post(
        '/doc',
        headers=auth(token),
        json={
            'name': 'Artigo',
            'identifier': 'ART-1',
            'description': 'Artigo do aluno',
        },
    )
    assert response.status_code == HTTPStatus.CREATED, response.text
    return response.json()


@pytest.fixture
def release(session, doc, user):
    async def _release():
        item = DocumentRelease(
            document_id=UUID(doc['id']), file_path='/uploads/artigo.pdf'
        )
        item.set_creation_audit(user.id)
        session.add(item)
        await session.commit()
        return item

    return _release


@pytest.mark.parametrize(
    ('method', 'path', 'body'),
    [
        ('GET', '/doc/{id}/release', None),
        ('GET', '/doc/{id}/messages', None),
        ('POST', '/doc/{id}/message', {'content': 'oi'}),
        ('POST', '/doc/{id}/assistant/chat', {'message': 'oi'}),
        ('GET', '/advisorship/documents/{id}/academic-context', None),
    ],
)
def test_estranho_nao_alcanca_dados_do_documento(
    client, doc, other_token, method, path, body
):
    response = client.request(
        method,
        path.format(id=doc['id']),
        headers=auth(other_token),
        json=body,
    )
    assert response.status_code == HTTPStatus.FORBIDDEN, response.text


def test_estranho_nao_abre_conversa(client, doc, other_token):
    response = client.post(
        '/chat/conversations',
        headers=auth(other_token),
        json={'document_id': doc['id']},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_estranho_nao_le_mensagem_por_id(
    client, session, doc, user, other_token
):
    message = DocumentMessage(
        content='nota',
        references=[],
        document_id=UUID(doc['id']),
        release_id=None,
        author_id=user.id,
        created_by=user.id,
    )
    session.add(message)
    await session.commit()

    response = client.get(
        f'/doc/message/{message.id}', headers=auth(other_token)
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_estranho_nao_exporta_pdf(client, release, other_token):
    item = await release()

    response = client.get(
        '/export/release/pdf',
        headers=auth(other_token),
        params={'document_release_id': str(item.id)},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


@patch('lumina.routers.docs.releases.release_pipeline', new_callable=AsyncMock)
def test_estranho_nao_envia_release(_pipeline, client, doc, other_token):
    response = client.post(
        f'/doc/{doc["id"]}/release',
        headers=auth(other_token),
        files={'file': ('a.pdf', b'%PDF-1.4', 'application/pdf')},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_editor_nao_remove_release(
    client, doc, token, other_user, other_token, release
):
    client.put(
        '/doc',
        headers=auth(token),
        json={
            'id': doc['id'],
            'name': doc['name'],
            'identifier': doc['identifier'],
            'description': doc['description'],
            'editors_ids': [str(other_user.id)],
        },
    )
    item = await release()

    response = client.delete(
        f'/doc/{doc["id"]}/release/{item.id}', headers=auth(other_token)
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_autor_remove_release(client, doc, token, release):
    item = await release()

    response = client.delete(
        f'/doc/{doc["id"]}/release/{item.id}', headers=auth(token)
    )
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.asyncio
async def test_orientador_ativo_posta_mensagem(
    client, session, doc, user, other_user, other_token, release
):
    await release()
    advisorship = Advisorship(
        advisor_id=other_user.id, advisee_id=user.id, status='ACTIVE'
    )
    advisorship.set_creation_audit(other_user.id)
    session.add(advisorship)
    await session.commit()

    response = client.post(
        f'/doc/{doc["id"]}/message',
        headers=auth(other_token),
        json={'content': 'Revise a introdução'},
    )
    assert response.status_code == HTTPStatus.CREATED, response.text


@pytest_asyncio.fixture
async def message(client, doc, token, release):
    await release()
    response = client.post(
        f'/doc/{doc["id"]}/message',
        headers=auth(token),
        json={'content': 'Primeira versão'},
    )
    assert response.status_code == HTTPStatus.CREATED, response.text
    return response.json()


@pytest.mark.asyncio
async def test_autor_edita_a_propria_mensagem(client, message, token):
    response = client.put(
        '/doc/message',
        headers=auth(token),
        json={'id': message['id'], 'content': 'Editada'},
    )
    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_orientador_nao_edita_mensagem_do_aluno(
    client, session, message, user, other_user, other_token
):
    advisorship = Advisorship(
        advisor_id=other_user.id, advisee_id=user.id, status='ACTIVE'
    )
    advisorship.set_creation_audit(other_user.id)
    session.add(advisorship)
    await session.commit()

    response = client.put(
        '/doc/message',
        headers=auth(other_token),
        json={'id': message['id'], 'content': 'Editada'},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN

    response = client.delete(
        f'/doc/message/{message["id"]}', headers=auth(other_token)
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_usuario_nao_liga_documento_a_projeto_alheio(
    client, session, other_user, token
):
    project = Project(name='Projeto alheio', description='Outro')
    project.set_creation_audit(other_user.id)
    session.add(project)
    await session.flush()
    project_doc = ProjectDocument(project_id=project.id, name='Artigo')
    project_doc.set_creation_audit(other_user.id)
    session.add(project_doc)
    await session.commit()

    response = client.post(
        '/doc',
        headers=auth(token),
        json={
            'name': 'Intruso',
            'identifier': 'INT-1',
            'description': 'x',
            'project_document_id': str(project_doc.id),
        },
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
