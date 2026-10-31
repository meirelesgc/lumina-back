from http import HTTPStatus
from uuid import uuid4

import pytest

from lumina.core.security import create_access_token
from lumina.models import Advisorship, Project, User
from lumina.schemas.user import AccessType


@pytest.fixture
def advisee_and_project(session, user):
    user.access_level = AccessType.ADMIN
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


@pytest.mark.asyncio
async def test_cartao_de_orientando_nao_traz_pendencias(
    client, session, user, token, advisee_and_project
):
    advisee, _ = advisee_and_project
    session.add(advisee)
    await session.commit()

    client.post(
        '/advisorship',
        headers={'Authorization': f'Bearer {token}'},
        json={'advisor_id': str(user.id), 'advisee_id': str(advisee.id)},
    )

    card = client.get(
        '/advisorship/my-advisees',
        headers={'Authorization': f'Bearer {token}'},
    ).json()['advisees'][0]

    assert card['total_documents'] == 0
    assert 'pending_reviews' not in card


@pytest.mark.asyncio
async def test_get_my_advisees_with_deleted_advisee(
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
            'topic': 'Tema Deletado',
        },
    )
    assert resp_create.status_code == HTTPStatus.CREATED

    # Simula soft delete do advisee (aluno deletado)
    advisee.set_deletion_audit(user.id)
    await session.commit()

    resp_advisees = client.get(
        '/advisorship/my-advisees',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp_advisees.status_code == HTTPStatus.OK
    advisees_list = resp_advisees.json()['advisees']
    assert len(advisees_list) == 0


@pytest.mark.asyncio
async def test_get_my_advisors_with_deleted_advisor(
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
            'topic': 'Tema Orientador Deletado',
        },
    )
    assert resp_create.status_code == HTTPStatus.CREATED

    # Simula soft delete do orientador
    user.set_deletion_audit(user.id)
    await session.commit()

    advisee_token = create_access_token({'sub': str(advisee.id)})
    resp_advisors = client.get(
        '/advisorship/my-advisors',
        headers={'Authorization': f'Bearer {advisee_token}'},
    )
    assert resp_advisors.status_code == HTTPStatus.OK
    advisors_list = resp_advisors.json()['advisors']
    assert len(advisors_list) == 0


def auth(token):
    return {'Authorization': f'Bearer {token}'}


def test_usuario_nao_se_declara_orientador_de_outro(
    client, user, other_user, token
):
    response = client.post(
        '/advisorship',
        headers=auth(token),
        json={'advisor_id': str(user.id), 'advisee_id': str(other_user.id)},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_orientando_nao_escolhe_orientador_comum(
    client, user, other_user, token
):
    response = client.post(
        '/advisorship',
        headers=auth(token),
        json={'advisor_id': str(other_user.id), 'advisee_id': str(user.id)},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_orientando_escolhe_orientador_admin(
    client, user, admin_user, token
):
    response = client.post(
        '/advisorship',
        headers=auth(token),
        json={'advisor_id': str(admin_user.id), 'advisee_id': str(user.id)},
    )
    assert response.status_code == HTTPStatus.CREATED


def test_admin_cria_vinculo_entre_terceiros(
    client, user, other_user, admin_token
):
    response = client.post(
        '/advisorship',
        headers=auth(admin_token),
        json={'advisor_id': str(user.id), 'advisee_id': str(other_user.id)},
    )
    assert response.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
async def test_orientando_nao_usa_projeto_de_terceiro(
    client, session, user, other_user, admin_user, token
):
    project = Project(name='Projeto alheio', description='Outro')
    project.set_creation_audit(other_user.id)
    session.add(project)
    await session.commit()

    response = client.post(
        '/advisorship',
        headers=auth(token),
        json={
            'advisor_id': str(admin_user.id),
            'advisee_id': str(user.id),
            'project_id': str(project.id),
        },
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.fixture
def link(session, user, other_user):
    async def _link(status, project_id=None):
        advisorship = Advisorship(
            advisor_id=user.id,
            advisee_id=other_user.id,
            project_id=project_id,
            status=status,
        )
        advisorship.set_creation_audit(user.id)
        session.add(advisorship)
        await session.commit()
        return advisorship

    return _link


@pytest.mark.asyncio
async def test_orientador_comum_nao_reativa_vinculo(client, link, token):
    advisorship = await link('CANCELLED')

    response = client.put(
        f'/advisorship/{advisorship.id}',
        headers=auth(token),
        json={'status': 'ACTIVE'},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_admin_reativa_vinculo(client, link, admin_token):
    advisorship = await link('CANCELLED')

    response = client.put(
        f'/advisorship/{advisorship.id}',
        headers=auth(admin_token),
        json={'status': 'ACTIVE'},
    )
    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.parametrize('status', ['CANCELLED', 'COMPLETED'])
async def test_ex_orientador_nao_lista_documentos(
    client, link, other_user, token, status
):
    await link(status)

    response = client.get(
        f'/advisorship/advisees/{other_user.id}/documents',
        headers=auth(token),
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_orientador_ativo_em_outro_projeto_lista_documentos(
    client, session, link, user, other_user, token
):
    project = Project(name='Projeto ativo', description='Ativo')
    project.set_creation_audit(other_user.id)
    session.add(project)
    await session.commit()
    await link('ACTIVE', project.id)

    response = client.get(
        f'/advisorship/advisees/{other_user.id}/documents',
        headers=auth(token),
    )
    assert response.status_code == HTTPStatus.OK


def test_usuario_comum_nao_envia_convite(client, token):
    response = client.post(
        '/invitations',
        headers=auth(token),
        json={'email': 'convidado@example.com'},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
