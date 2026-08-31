from http import HTTPStatus
from uuid import uuid4

import pytest

from lumina.core.security import create_access_token
from lumina.models import AccessType, Advisorship, User


@pytest.fixture
def auth_header_for_user():
    def _generator(user: User):
        token = create_access_token({'sub': str(user.id)})
        return {'Authorization': f'Bearer {token}'}

    return _generator


@pytest.mark.asyncio
async def test_user_sees_only_own_projects_by_default(
    client, session, auth_header_for_user
):
    user_a = User(
        username='user_proj_a',
        email='user_proj_a@teste.com',
        password='hash',
        phone_number='5511999991001',
        access_level=AccessType.DEFAULT,
    )
    user_b = User(
        username='user_proj_b',
        email='user_proj_b@teste.com',
        password='hash',
        phone_number='5511999991002',
        access_level=AccessType.DEFAULT,
    )
    session.add_all([user_a, user_b])
    await session.commit()
    await session.refresh(user_a)
    await session.refresh(user_b)

    # User A cria Projeto A
    resp_a = client.post(
        '/project',
        headers=auth_header_for_user(user_a),
        json={'name': f'Projeto A {uuid4().hex[:6]}', 'description': 'Desc A'},
    )
    assert resp_a.status_code == HTTPStatus.CREATED
    proj_a_id = resp_a.json()['id']

    # User B cria Projeto B
    resp_b = client.post(
        '/project',
        headers=auth_header_for_user(user_b),
        json={'name': f'Projeto B {uuid4().hex[:6]}', 'description': 'Desc B'},
    )
    assert resp_b.status_code == HTTPStatus.CREATED
    proj_b_id = resp_b.json()['id']

    # User A lista projetos: vê apenas Projeto A
    list_a = client.get('/project', headers=auth_header_for_user(user_a))
    assert list_a.status_code == HTTPStatus.OK
    projects_a = list_a.json()['projects']
    assert any(p['id'] == proj_a_id for p in projects_a)
    assert not any(p['id'] == proj_b_id for p in projects_a)

    # User B lista projetos: vê apenas Projeto B
    list_b = client.get('/project', headers=auth_header_for_user(user_b))
    assert list_b.status_code == HTTPStatus.OK
    projects_b = list_b.json()['projects']
    assert any(p['id'] == proj_b_id for p in projects_b)
    assert not any(p['id'] == proj_a_id for p in projects_b)


@pytest.mark.asyncio
async def test_unauthorized_user_forbidden_project_access(
    client, session, auth_header_for_user
):
    owner = User(
        username='owner_proj',
        email='owner_proj@teste.com',
        password='hash',
        phone_number='5511999991003',
        access_level=AccessType.DEFAULT,
    )
    stranger = User(
        username='stranger_proj',
        email='stranger_proj@teste.com',
        password='hash',
        phone_number='5511999991004',
        access_level=AccessType.DEFAULT,
    )
    session.add_all([owner, stranger])
    await session.commit()
    await session.refresh(owner)
    await session.refresh(stranger)

    # Owner cria projeto
    proj_resp = client.post(
        '/project',
        headers=auth_header_for_user(owner),
        json={'name': f'Private Proj {uuid4().hex[:6]}'},
    )
    proj_id = proj_resp.json()['id']

    # Estranho tenta consultar por ID -> 403
    get_res = client.get(
        f'/project/{proj_id}', headers=auth_header_for_user(stranger)
    )
    assert get_res.status_code == HTTPStatus.FORBIDDEN

    # Estranho tenta atualizar projeto de outro -> 403
    put_res = client.put(
        '/project',
        headers=auth_header_for_user(stranger),
        json={'id': proj_id, 'name': 'Hacked Project'},
    )
    assert put_res.status_code == HTTPStatus.FORBIDDEN

    # Estranho tenta excluir projeto de outro -> 403
    del_res = client.delete(
        f'/project/{proj_id}', headers=auth_header_for_user(stranger)
    )
    assert del_res.status_code == HTTPStatus.FORBIDDEN

    # Estranho tenta ler documentos do projeto de outro -> 403
    docs_res = client.get(
        f'/project-document/by-project/{proj_id}',
        headers=auth_header_for_user(stranger),
    )
    assert docs_res.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_advisor_can_view_advisee_projects(
    client, session, auth_header_for_user
):
    advisor = User(
        username='prof_advisor_p',
        email='prof_advisor_p@teste.com',
        password='hash',
        phone_number='5511999991005',
        access_level=AccessType.DEFAULT,
    )
    advisee = User(
        username='aluno_advisee_p',
        email='aluno_advisee_p@teste.com',
        password='hash',
        phone_number='5511999991006',
        access_level=AccessType.DEFAULT,
    )
    session.add_all([advisor, advisee])
    await session.commit()
    await session.refresh(advisor)
    await session.refresh(advisee)

    # Cria vínculo de orientação ativo
    session.add(
        Advisorship(
            advisor_id=advisor.id,
            advisee_id=advisee.id,
            role_type='MAIN_ADVISOR',
            status='ACTIVE',
        )
    )
    await session.commit()

    # Advisee cria projeto
    proj_advisee_id = client.post(
        '/project',
        headers=auth_header_for_user(advisee),
        json={'name': f'TCC Advisee {uuid4().hex[:6]}'},
    ).json()['id']

    # Advisor cria projeto próprio
    proj_advisor_id = client.post(
        '/project',
        headers=auth_header_for_user(advisor),
        json={'name': f'Pesquisa Advisor {uuid4().hex[:6]}'},
    ).json()['id']

    headers = auth_header_for_user(advisor)

    # 1. Padrão (scope='mine'): Vê apenas o seu
    list_mine = client.get('/project', headers=headers).json()['projects']
    assert any(p['id'] == proj_advisor_id for p in list_mine)
    assert not any(p['id'] == proj_advisee_id for p in list_mine)

    # 2. scope='advisees': Vê os do orientando
    list_advisees = client.get(
        '/project?scope=advisees', headers=headers
    ).json()['projects']
    assert any(p['id'] == proj_advisee_id for p in list_advisees)
    assert not any(p['id'] == proj_advisor_id for p in list_advisees)

    # 3. scope='all': Vê os seus e os dos orientandos
    list_all = client.get('/project?scope=all', headers=headers).json()[
        'projects'
    ]
    assert any(p['id'] == proj_advisor_id for p in list_all)
    assert any(p['id'] == proj_advisee_id for p in list_all)

    # 4. Advisor pode consultar projeto do orientando por ID
    get_proj = client.get(f'/project/{proj_advisee_id}', headers=headers)
    assert get_proj.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_cancelled_advisorship_blocks_project_access(
    client, session, auth_header_for_user
):
    advisor = User(
        username='ex_prof_p',
        email='ex_prof_p@teste.com',
        password='hash',
        phone_number='5511999991007',
        access_level=AccessType.DEFAULT,
    )
    advisee = User(
        username='ex_aluno_p',
        email='ex_aluno_p@teste.com',
        password='hash',
        phone_number='5511999991008',
        access_level=AccessType.DEFAULT,
    )
    session.add_all([advisor, advisee])
    await session.commit()
    await session.refresh(advisor)
    await session.refresh(advisee)

    # Vínculo cancelado
    session.add(
        Advisorship(
            advisor_id=advisor.id,
            advisee_id=advisee.id,
            role_type='MAIN_ADVISOR',
            status='CANCELLED',
        )
    )
    await session.commit()

    proj_id = client.post(
        '/project',
        headers=auth_header_for_user(advisee),
        json={'name': f'Projeto Pos Cancelamento {uuid4().hex[:6]}'},
    ).json()['id']

    # Ex-orientador tenta listar com scope=advisees -> não retorna o projeto
    list_advisees = client.get(
        '/project?scope=advisees', headers=auth_header_for_user(advisor)
    ).json()['projects']
    assert not any(p['id'] == proj_id for p in list_advisees)

    # Ex-orientador tenta acessar por ID -> 403 Forbidden
    get_res = client.get(
        f'/project/{proj_id}', headers=auth_header_for_user(advisor)
    )
    assert get_res.status_code == HTTPStatus.FORBIDDEN
