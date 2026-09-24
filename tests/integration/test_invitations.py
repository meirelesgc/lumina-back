from datetime import datetime, timedelta, timezone
from http import HTTPStatus

import pytest
from sqlalchemy import select

from lumina.models import Advisorship, Invitation, User

EXPECTED_MIN_DAYS = 6
EXPECTED_MAX_DAYS = 7
MIN_INVITATIONS = 2


@pytest.mark.asyncio
async def test_create_invitation_success(client, user, token):
    response = client.post(
        '/invitations',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': 'aluno_novo@teste.com',
            'role_type': 'MAIN_ADVISOR',
            'topic': 'Inteligência Artificial na Saúde',
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['email'] == 'aluno_novo@teste.com'
    assert data['status'] == 'PENDING'
    assert data['role_type'] == 'MAIN_ADVISOR'
    assert data['topic'] == 'Inteligência Artificial na Saúde'
    assert data['token'] is not None
    assert data['expires_at'] is not None

    # Verifica validade em torno de 7 dias
    expires = datetime.fromisoformat(data['expires_at'])
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = expires - now
    assert EXPECTED_MIN_DAYS <= delta.days <= EXPECTED_MAX_DAYS


@pytest.mark.asyncio
async def test_create_invitation_cannot_invite_self(client, user, token):
    response = client.post(
        '/invitations',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': user.email,
            'role_type': 'MAIN_ADVISOR',
        },
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert 'próprio e-mail' in response.json()['detail']


@pytest.mark.asyncio
async def test_create_invitation_conflict_if_already_pending(
    client, user, token
):
    invite_payload = {
        'email': 'repetido@teste.com',
        'role_type': 'MAIN_ADVISOR',
    }
    res1 = client.post(
        '/invitations',
        headers={'Authorization': f'Bearer {token}'},
        json=invite_payload,
    )
    assert res1.status_code == HTTPStatus.CREATED

    res2 = client.post(
        '/invitations',
        headers={'Authorization': f'Bearer {token}'},
        json=invite_payload,
    )
    assert res2.status_code == HTTPStatus.CONFLICT
    assert 'Já existe um convite pendente' in res2.json()['detail']


@pytest.mark.asyncio
async def test_check_invitation_by_token(client, user, token):
    res_create = client.post(
        '/invitations',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': 'nao_cadastrado@teste.com',
            'topic': 'Genômica Funcional',
        },
    )
    assert res_create.status_code == HTTPStatus.CREATED
    invite_token = res_create.json()['token']

    # Endpoint público de verificação
    res_check = client.get(f'/invitations/{invite_token}')
    assert res_check.status_code == HTTPStatus.OK
    check_data = res_check.json()
    assert check_data['email'] == 'nao_cadastrado@teste.com'
    assert check_data['status'] == 'PENDING'
    assert check_data['is_valid'] is True
    assert check_data['is_expired'] is False
    assert check_data['user_exists'] is False
    assert check_data['inviter_name'] == user.username
    assert check_data['topic'] == 'Genômica Funcional'


@pytest.mark.asyncio
async def test_register_and_accept_invitation_single_step(
    client, session, user, token
):
    target_email = 'novo_estudante@teste.com'
    res_create = client.post(
        '/invitations',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': target_email,
            'topic': 'Bioinformática',
        },
    )
    assert res_create.status_code == HTTPStatus.CREATED
    invite_token = res_create.json()['token']

    # Cadastro e aceite em passo único via link compartilhado (público)
    res_reg = client.post(
        f'/invitations/{invite_token}/register',
        json={
            'username': 'estudante_bioinfo',
            'phone_number': '5511987654321',
            'password': 'Password123!',
        },
    )
    assert res_reg.status_code == HTTPStatus.CREATED
    data = res_reg.json()
    assert data['invitation']['status'] == 'ACCEPTED'
    assert data['token']['access_token'] is not None

    # Verifica se usuário foi criado no banco
    stmt_user = select(User).where(User.email == target_email)
    created_user = await session.scalar(stmt_user)
    assert created_user is not None
    assert created_user.username == 'estudante_bioinfo'

    # Verifica se vínculo Advisorship foi estabelecido
    stmt_adv = select(Advisorship).where(
        Advisorship.advisor_id == user.id,
        Advisorship.advisee_id == created_user.id,
    )
    adv = await session.scalar(stmt_adv)
    assert adv is not None
    assert adv.status == 'ACTIVE'
    assert adv.topic == 'Bioinformática'


@pytest.mark.asyncio
async def test_accept_invitation_with_existing_user(
    client, session, user, other_user, token
):
    # Criar convite para other_user
    res_create = client.post(
        '/invitations',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': other_user.email,
            'topic': 'Epidemiologia',
        },
    )
    assert res_create.status_code == HTTPStatus.CREATED
    invite_token = res_create.json()['token']

    # Login do other_user
    res_login = client.post(
        '/auth/token',
        data={
            'username': other_user.email,
            'password': other_user.clean_password,
        },
    )
    other_token = res_login.json()['access_token']

    # Outro usuário aceita
    res_accept = client.post(
        f'/invitations/{invite_token}/accept',
        headers={'Authorization': f'Bearer {other_token}'},
    )
    assert res_accept.status_code == HTTPStatus.OK
    data = res_accept.json()
    assert data['invitation']['status'] == 'ACCEPTED'
    assert data['advisorship'] is not None
    assert data['advisorship']['status'] == 'ACTIVE'
    assert data['advisorship']['advisor_id'] == str(user.id)
    assert data['advisorship']['advisee_id'] == str(other_user.id)


@pytest.mark.asyncio
async def test_accept_invitation_wrong_user_forbidden(
    client, session, user, other_user, token
):
    # Convite emitido para um terceiro email
    res_create = client.post(
        '/invitations',
        headers={'Authorization': f'Bearer {token}'},
        json={'email': 'terceiro@teste.com'},
    )
    invite_token = res_create.json()['token']

    # other_user tenta aceitar convite emitido para 'terceiro@teste.com'
    res_login = client.post(
        '/auth/token',
        data={
            'username': other_user.email,
            'password': other_user.clean_password,
        },
    )
    other_token = res_login.json()['access_token']

    res_accept = client.post(
        f'/invitations/{invite_token}/accept',
        headers={'Authorization': f'Bearer {other_token}'},
    )
    assert res_accept.status_code == HTTPStatus.FORBIDDEN
    assert 'outro e-mail' in res_accept.json()['detail']


@pytest.mark.asyncio
async def test_reject_invitation(client, session, user, token):
    res_create = client.post(
        '/invitations',
        headers={'Authorization': f'Bearer {token}'},
        json={'email': 'recusador@teste.com'},
    )
    invite_token = res_create.json()['token']

    res_reject = client.post(f'/invitations/{invite_token}/reject')
    assert res_reject.status_code == HTTPStatus.OK

    # Consulta para confirmar status REJECTED
    res_check = client.get(f'/invitations/{invite_token}')
    assert res_check.json()['status'] == 'REJECTED'
    assert res_check.json()['is_valid'] is False


@pytest.mark.asyncio
async def test_cancel_invitation(client, user, token):
    res_create = client.post(
        '/invitations',
        headers={'Authorization': f'Bearer {token}'},
        json={'email': 'para_cancelar@teste.com'},
    )
    assert res_create.status_code == HTTPStatus.CREATED
    data = res_create.json()
    invitation_id = data['id']
    invite_token = data['token']

    res_cancel = client.delete(
        f'/invitations/{invitation_id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert res_cancel.status_code == HTTPStatus.OK

    # Convite cancelado/excluído não deve ser acessível por token
    res_check = client.get(f'/invitations/{invite_token}')
    assert res_check.status_code == HTTPStatus.NOT_FOUND

    # Não deve mais constar na lista de convites
    res_list = client.get(
        '/invitations',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert res_list.status_code == HTTPStatus.OK
    ids = [i['id'] for i in res_list.json()['invitations']]
    assert invitation_id not in ids


@pytest.mark.asyncio
async def test_list_invitations(client, user, token):
    client.post(
        '/invitations',
        headers={'Authorization': f'Bearer {token}'},
        json={'email': 'convidado1@teste.com'},
    )
    client.post(
        '/invitations',
        headers={'Authorization': f'Bearer {token}'},
        json={'email': 'convidado2@teste.com'},
    )

    res_list = client.get(
        '/invitations',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert res_list.status_code == HTTPStatus.OK
    invitations = res_list.json()['invitations']
    assert len(invitations) >= MIN_INVITATIONS
    emails = [i['email'] for i in invitations]
    assert 'convidado1@teste.com' in emails
    assert 'convidado2@teste.com' in emails


@pytest.mark.asyncio
async def test_list_pending_for_me_unauthenticated(client):
    response = client.get('/invitations/pending-for-me')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_list_pending_for_me_empty(client, user, token):
    response = client.get(
        '/invitations/pending-for-me',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['invitations'] == []


@pytest.mark.asyncio
async def test_list_pending_for_me_multiple_invitations(
    client, session, user, other_user, token
):
    # user cria convite para other_user
    res1 = client.post(
        '/invitations',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': other_user.email,
            'topic': 'Projeto de Tese 1',
        },
    )
    assert res1.status_code == HTTPStatus.CREATED

    # Login de other_user
    res_login = client.post(
        '/auth/token',
        data={
            'username': other_user.email,
            'password': other_user.clean_password,
        },
    )
    other_token = res_login.json()['access_token']

    # other_user consulta seus convites pendentes
    res_list = client.get(
        '/invitations/pending-for-me',
        headers={'Authorization': f'Bearer {other_token}'},
    )
    assert res_list.status_code == HTTPStatus.OK
    invitations = res_list.json()['invitations']
    assert len(invitations) == 1
    assert invitations[0]['email'] == other_user.email
    assert invitations[0]['status'] == 'PENDING'
    assert invitations[0]['topic'] == 'Projeto de Tese 1'
    assert invitations[0]['inviter'] is not None
    assert invitations[0]['inviter']['email'] == user.email


@pytest.mark.asyncio
async def test_list_pending_for_me_excludes_expired_and_accepted(
    client, session, user, other_user, token
):
    # user cria convite 1
    res1 = client.post(
        '/invitations',
        headers={'Authorization': f'Bearer {token}'},
        json={'email': other_user.email, 'topic': 'Convite Valido'},
    )
    assert res1.status_code == HTTPStatus.CREATED
    valid_id = res1.json()['id']

    # Login de other_user
    res_login = client.post(
        '/auth/token',
        data={
            'username': other_user.email,
            'password': other_user.clean_password,
        },
    )
    other_token = res_login.json()['access_token']

    # Criar convite expirado diretamente no banco
    expired_invitation = Invitation(
        email=other_user.email,
        inviter_id=user.id,
        token='expired_token_123',
        topic='Convite Expirado',
        status='PENDING',
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    session.add(expired_invitation)
    await session.commit()

    # other_user consulta seus convites pendentes
    res_list = client.get(
        '/invitations/pending-for-me',
        headers={'Authorization': f'Bearer {other_token}'},
    )
    assert res_list.status_code == HTTPStatus.OK
    invitations = res_list.json()['invitations']
    # Apenas o convite válido deve vir
    assert len(invitations) == 1
    assert invitations[0]['id'] == valid_id
    assert invitations[0]['topic'] == 'Convite Valido'
