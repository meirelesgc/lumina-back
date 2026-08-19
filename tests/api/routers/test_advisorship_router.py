from http import HTTPStatus
from uuid import uuid4

import pytest

from lumina.core.security import create_access_token
from lumina.models import Project, User
from lumina.schemas.user import AccessType


@pytest.fixture
def advisee_and_project(session, user):
    advisee = User(
        username=f'advisee_{uuid4().hex[:6]}',
        email=f'advisee_{uuid4().hex[:6]}@test.com',
        phone_number=f'55019{uuid4().int % 100000000:08d}',
        password='hash',
        access_level=AccessType.DEFAULT,
    )
    project = Project(
        name=f'Projeto TCC {uuid4().hex[:6]}',
        description='Descricao do projeto',
    )
    project.set_creation_audit(user.id)
    return advisee, project


@pytest.mark.asyncio
async def test_create_and_query_advisorship(
    client, session, user, token, advisee_and_project
):
    advisee, project = advisee_and_project
    session.add_all([advisee, project])
    await session.commit()

    # 1. Criar vínculo
    payload = {
        'advisor_id': str(user.id),
        'advisee_id': str(advisee.id),
        'project_id': str(project.id),
        'role_type': 'MAIN_ADVISOR',
        'topic': 'Machine Learning em Grafos',
    }
    resp = client.post(
        '/advisorship',
        headers={'Authorization': f'Bearer {token}'},
        json=payload,
    )
    assert resp.status_code == HTTPStatus.CREATED
    created = resp.json()
    assert created['advisor_id'] == str(user.id)
    assert created['advisee_id'] == str(advisee.id)

    # 2. Listar meus orientandos (Visão 1)
    resp_advisees = client.get(
        '/advisorship/my-advisees',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp_advisees.status_code == HTTPStatus.OK
    advisees_list = resp_advisees.json()['advisees']
    assert any(a['advisee']['id'] == str(advisee.id) for a in advisees_list)

    # 3. Listar meus orientadores como Orientando (Visão 3)
    advisee_token = create_access_token({'sub': str(advisee.id)})
    resp_advisors = client.get(
        '/advisorship/my-advisors',
        headers={'Authorization': f'Bearer {advisee_token}'},
    )
    assert resp_advisors.status_code == HTTPStatus.OK
    advisors_list = resp_advisors.json()['advisors']
    assert any(a['advisor']['id'] == str(user.id) for a in advisors_list)


@pytest.mark.asyncio
async def test_advisorship_documents_and_context(
    client, session, user, token, advisee_and_project
):
    advisee, project = advisee_and_project
    session.add_all([advisee, project])
    await session.commit()

    # Cria vínculo
    resp_adv = client.post(
        '/advisorship',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'advisor_id': str(user.id),
            'advisee_id': str(advisee.id),
            'project_id': str(project.id),
        },
    )
    assert resp_adv.status_code == HTTPStatus.CREATED

    # Cria documento
    resp_doc = client.post(
        '/doc',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'name': 'Monografia Preliminar',
            'identifier': f'MONO-{uuid4().hex[:6]}',
            'description': 'Primeira versao da monografia',
            'grupo': 'TCC',
            'tipo_documento': 'Monografia',
            'projeto_nome': project.name,
            'typification_ids': None,
            'editors_ids': None,
        },
    )
    assert resp_doc.status_code == HTTPStatus.CREATED
    doc_id = resp_doc.json()['id']

    # Visão 1: Documentos do orientando
    resp_docs = client.get(
        f'/advisorship/advisees/{advisee.id}/documents',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp_docs.status_code == HTTPStatus.OK

    # Visão 2: Contexto acadêmico do documento
    resp_ctx = client.get(
        f'/advisorship/documents/{doc_id}/academic-context',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp_ctx.status_code == HTTPStatus.OK
    assert resp_ctx.json()['document_id'] == doc_id


@pytest.mark.asyncio
async def test_advisorship_update_and_delete(
    client, session, user, token, advisee_and_project
):
    advisee, _ = advisee_and_project
    session.add(advisee)
    await session.commit()

    resp_create = client.post(
        '/advisorship',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'advisor_id': str(user.id),
            'advisee_id': str(advisee.id),
            'topic': 'Tema Inicial',
        },
    )
    advisorship_id = resp_create.json()['id']

    resp_up = client.put(
        f'/advisorship/{advisorship_id}',
        headers={'Authorization': f'Bearer {token}'},
        json={'topic': 'Tema Atualizado', 'status': 'COMPLETED'},
    )
    assert resp_up.status_code == HTTPStatus.OK
    assert resp_up.json()['topic'] == 'Tema Atualizado'

    resp_del = client.delete(
        f'/advisorship/{advisorship_id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp_del.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_advisorship_unauthorized(client):
    response = client.get('/advisorship/my-advisees')
    assert response.status_code == HTTPStatus.UNAUTHORIZED
