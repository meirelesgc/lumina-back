from http import HTTPStatus
from uuid import uuid4

import pytest

from lumina.core.security import create_access_token
from lumina.models import Advisorship, User
from lumina.schemas.user import AccessType


@pytest.fixture
def auth_header_for_user():
    def _generator(user: User):
        token = create_access_token({'sub': str(user.id)})
        return {'Authorization': f'Bearer {token}'}

    return _generator


@pytest.mark.asyncio
async def test_user_sees_only_own_documents_by_default(
    client, session, auth_header_for_user
):
    user_a = User(
        username='user_a',
        email='user_a@teste.com',
        password='hash',
        phone_number='5511999990001',
        access_level=AccessType.DEFAULT,
    )
    user_b = User(
        username='user_b',
        email='user_b@teste.com',
        password='hash',
        phone_number='5511999990002',
        access_level=AccessType.DEFAULT,
    )
    session.add_all([user_a, user_b])
    await session.commit()
    await session.refresh(user_a)
    await session.refresh(user_b)

    # User A cria Doc A
    resp_a = client.post(
        '/doc',
        headers=auth_header_for_user(user_a),
        json={
            'name': 'Doc A',
            'identifier': f'DOC-A-{uuid4().hex[:6]}',
            'description': 'Desc A',
        },
    )
    assert resp_a.status_code == HTTPStatus.CREATED
    doc_a_id = resp_a.json()['id']

    # User B cria Doc B
    resp_b = client.post(
        '/doc',
        headers=auth_header_for_user(user_b),
        json={
            'name': 'Doc B',
            'identifier': f'DOC-B-{uuid4().hex[:6]}',
            'description': 'Desc B',
        },
    )
    assert resp_b.status_code == HTTPStatus.CREATED
    doc_b_id = resp_b.json()['id']

    # User A lista /doc
    list_a = client.get('/doc', headers=auth_header_for_user(user_a))
    assert list_a.status_code == HTTPStatus.OK
    docs_a = list_a.json()['documents']
    assert any(d['id'] == doc_a_id for d in docs_a)
    assert not any(d['id'] == doc_b_id for d in docs_a)

    # User B lista /doc
    list_b = client.get('/doc', headers=auth_header_for_user(user_b))
    assert list_b.status_code == HTTPStatus.OK
    docs_b = list_b.json()['documents']
    assert any(d['id'] == doc_b_id for d in docs_b)
    assert not any(d['id'] == doc_a_id for d in docs_b)


@pytest.mark.asyncio
async def test_user_sees_document_where_they_are_editor(
    client, session, auth_header_for_user
):
    user_author = User(
        username='author_doc',
        email='author@teste.com',
        password='hash',
        phone_number='5511999990003',
        access_level=AccessType.DEFAULT,
    )
    user_editor = User(
        username='editor_doc',
        email='editor@teste.com',
        password='hash',
        phone_number='5511999990004',
        access_level=AccessType.DEFAULT,
    )
    session.add_all([user_author, user_editor])
    await session.commit()
    await session.refresh(user_author)
    await session.refresh(user_editor)

    # Autor cria documento adicionando editor
    ident = f'DOC-SHARED-{uuid4().hex[:6]}'
    resp = client.post(
        '/doc',
        headers=auth_header_for_user(user_author),
        json={
            'name': 'Doc Compartilhado',
            'identifier': ident,
            'description': 'Doc compartilhado com editor',
            'editors_ids': [str(user_editor.id)],
        },
    )
    assert resp.status_code == HTTPStatus.CREATED
    doc_id = resp.json()['id']

    # Editor lista /doc e deve enxergar o doc compartilhado
    list_resp = client.get('/doc', headers=auth_header_for_user(user_editor))
    assert list_resp.status_code == HTTPStatus.OK
    docs = list_resp.json()['documents']
    assert any(d['id'] == doc_id for d in docs)

    # Editor lê o doc por ID
    get_resp = client.get(
        f'/doc/{doc_id}', headers=auth_header_for_user(user_editor)
    )
    assert get_resp.status_code == HTTPStatus.OK
    assert get_resp.json()['name'] == 'Doc Compartilhado'

    # Editor pode atualizar o doc
    put_resp = client.put(
        '/doc',
        headers=auth_header_for_user(user_editor),
        json={
            'id': doc_id,
            'name': 'Doc Compartilhado Atualizado pelo Editor',
            'identifier': ident,
            'description': 'Nova descricao',
        },
    )
    assert put_resp.status_code == HTTPStatus.OK
    assert (
        put_resp.json()['name']
        == 'Doc Compartilhado Atualizado pelo Editor'
    )


@pytest.mark.asyncio
async def test_unauthorized_user_forbidden_access(
    client, session, auth_header_for_user
):
    user_owner = User(
        username='user_owner',
        email='owner@teste.com',
        password='hash',
        phone_number='5511999990005',
        access_level=AccessType.DEFAULT,
    )
    user_stranger = User(
        username='user_stranger',
        email='stranger@teste.com',
        password='hash',
        phone_number='5511999990006',
        access_level=AccessType.DEFAULT,
    )
    session.add_all([user_owner, user_stranger])
    await session.commit()
    await session.refresh(user_owner)
    await session.refresh(user_stranger)

    ident = f'DOC-PRIVATE-{uuid4().hex[:6]}'
    resp = client.post(
        '/doc',
        headers=auth_header_for_user(user_owner),
        json={
            'name': 'Doc Privado',
            'identifier': ident,
            'description': 'Apenas do dono',
        },
    )
    doc_id = resp.json()['id']

    # Estranho tenta ler por ID
    get_resp = client.get(
        f'/doc/{doc_id}', headers=auth_header_for_user(user_stranger)
    )
    assert get_resp.status_code == HTTPStatus.FORBIDDEN

    # Estranho tenta atualizar
    put_resp = client.put(
        '/doc',
        headers=auth_header_for_user(user_stranger),
        json={
            'id': doc_id,
            'name': 'Hacked',
            'identifier': ident,
            'description': 'Hacked',
        },
    )
    assert put_resp.status_code == HTTPStatus.FORBIDDEN

    # Estranho tenta deletar
    del_resp = client.delete(
        f'/doc/{doc_id}', headers=auth_header_for_user(user_stranger)
    )
    assert del_resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_advisor_access_and_scope_filtering(
    client, session, auth_header_for_user
):
    advisor = User(
        username='prof_advisor',
        email='advisor@universidade.edu.br',
        password='hash',
        phone_number='5511999990007',
        access_level=AccessType.DEFAULT,
    )
    advisee = User(
        username='aluno_advisee',
        email='advisee@universidade.edu.br',
        password='hash',
        phone_number='5511999990008',
        access_level=AccessType.DEFAULT,
    )
    session.add_all([advisor, advisee])
    await session.commit()
    await session.refresh(advisor)
    await session.refresh(advisee)

    # Cria vínculo ativo de orientação
    session.add(
        Advisorship(
            advisor_id=advisor.id,
            advisee_id=advisee.id,
            role_type='MAIN_ADVISOR',
            topic='Pesquisa de Mestrado',
            status='ACTIVE',
        )
    )
    await session.commit()

    # Advisee cria documento
    doc_advisee_id = client.post(
        '/doc',
        headers=auth_header_for_user(advisee),
        json={
            'name': 'Monografia do Orientando',
            'identifier': f'MONO-{uuid4().hex[:6]}',
            'description': 'Capitulos 1 a 3',
        },
    ).json()['id']

    # Advisor cria documento proprio
    doc_advisor_id = client.post(
        '/doc',
        headers=auth_header_for_user(advisor),
        json={
            'name': 'Artigo do Orientador',
            'identifier': f'ART-{uuid4().hex[:6]}',
            'description': 'Artigo pessoal',
        },
    ).json()['id']

    headers = auth_header_for_user(advisor)

    # 1. Padrão (scope='mine'): Advisor vê apenas o seu
    docs_mine = client.get('/doc', headers=headers).json()['documents']
    assert any(d['id'] == doc_advisor_id for d in docs_mine)
    assert not any(d['id'] == doc_advisee_id for d in docs_mine)

    # 2. scope='advisees': Advisor vê os do orientando
    docs_advisees = client.get(
        '/doc?scope=advisees', headers=headers
    ).json()['documents']
    assert any(d['id'] == doc_advisee_id for d in docs_advisees)
    assert not any(d['id'] == doc_advisor_id for d in docs_advisees)

    # 3. scope='all': Advisor vê os seus e os do orientando
    resp_all = client.get('/doc?scope=all', headers=headers)
    docs_all = resp_all.json()['documents']
    assert any(d['id'] == doc_advisor_id for d in docs_all)
    assert any(d['id'] == doc_advisee_id for d in docs_all)

    # 4. advisee_id específico
    docs_by_id = client.get(
        f'/doc?advisee_id={advisee.id}', headers=headers
    ).json()['documents']
    assert any(d['id'] == doc_advisee_id for d in docs_by_id)

    # 5. Advisor pode ler o documento do orientando diretamente por ID
    get_doc = client.get(f'/doc/{doc_advisee_id}', headers=headers)
    assert get_doc.status_code == HTTPStatus.OK
    assert get_doc.json()['name'] == 'Monografia do Orientando'


@pytest.mark.asyncio
async def test_cancelled_advisorship_blocks_access(
    client, session, auth_header_for_user
):
    advisor = User(
        username='ex_advisor',
        email='ex_advisor@teste.com',
        password='hash',
        phone_number='5511999990009',
        access_level=AccessType.DEFAULT,
    )
    advisee = User(
        username='ex_advisee',
        email='ex_advisee@teste.com',
        password='hash',
        phone_number='5511999990010',
        access_level=AccessType.DEFAULT,
    )
    session.add_all([advisor, advisee])
    await session.commit()
    await session.refresh(advisor)
    await session.refresh(advisee)

    # Vínculo cancelado
    advisorship = Advisorship(
        advisor_id=advisor.id,
        advisee_id=advisee.id,
        role_type='MAIN_ADVISOR',
        topic='Pesquisa Cancelada',
        status='CANCELLED',
    )
    session.add(advisorship)
    await session.commit()

    doc_resp = client.post(
        '/doc',
        headers=auth_header_for_user(advisee),
        json={
            'name': 'Trabalho Solitário',
            'identifier': f'SOL-{uuid4().hex[:6]}',
            'description': 'Sem orientador',
        },
    )
    doc_id = doc_resp.json()['id']

    # Ex-advisor tenta buscar por scope=advisees
    list_advisees = client.get(
        '/doc?scope=advisees', headers=auth_header_for_user(advisor)
    )
    assert list_advisees.status_code == HTTPStatus.OK
    docs = list_advisees.json()['documents']
    assert not any(d['id'] == doc_id for d in docs)

    # Ex-advisor tenta ler por ID -> 403
    get_resp = client.get(
        f'/doc/{doc_id}', headers=auth_header_for_user(advisor)
    )
    assert get_resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_admin_sees_all_documents_with_scope_all(
    client, session, auth_header_for_user
):
    admin = User(
        username='admin_user',
        email='admin@lumina.com',
        password='hash',
        phone_number='5511999990011',
        access_level=AccessType.ADMIN,
    )
    student = User(
        username='student_user',
        email='student@lumina.com',
        password='hash',
        phone_number='5511999990012',
        access_level=AccessType.DEFAULT,
    )
    session.add_all([admin, student])
    await session.commit()
    await session.refresh(admin)
    await session.refresh(student)

    # Estudante cria documento
    doc_resp = client.post(
        '/doc',
        headers=auth_header_for_user(student),
        json={
            'name': 'Doc do Estudante',
            'identifier': f'STUD-{uuid4().hex[:6]}',
            'description': 'Doc criado pelo estudante',
        },
    )
    doc_id = doc_resp.json()['id']

    # Admin com scope=all enxerga todos os documentos
    list_resp = client.get(
        '/doc?scope=all', headers=auth_header_for_user(admin)
    )
    assert list_resp.status_code == HTTPStatus.OK
    docs = list_resp.json()['documents']
    assert any(d['id'] == doc_id for d in docs)

    # Admin pode ler o documento por ID
    get_resp = client.get(
        f'/doc/{doc_id}', headers=auth_header_for_user(admin)
    )
    assert get_resp.status_code == HTTPStatus.OK
