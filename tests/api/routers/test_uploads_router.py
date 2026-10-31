from http import HTTPStatus
from uuid import UUID

import pytest

from lumina.models import DocumentRelease, UserImage


def auth(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(
        'lumina.services.upload_service.UPLOAD_DIRECTORY', tmp_path
    )
    return tmp_path


@pytest.fixture
def stored(uploads):
    def _stored(name):
        (uploads / name).write_bytes(b'%PDF-1.4')
        return f'/uploads/{name}'

    return _stored


@pytest.fixture
def doc(client, token):
    return client.post(
        '/doc',
        headers=auth(token),
        json={'name': 'Artigo', 'identifier': 'UP-1', 'description': 'x'},
    ).json()


async def attach_release(session, doc, user, file_path):
    release = DocumentRelease(document_id=UUID(doc['id']), file_path=file_path)
    release.set_creation_audit(user.id)
    session.add(release)
    await session.commit()


@pytest.mark.asyncio
async def test_autor_baixa_o_proprio_release(
    client, session, user, doc, stored, token
):
    url = stored('artigo.pdf')
    await attach_release(session, doc, user, url)

    response = client.get(url, headers=auth(token))

    assert response.status_code == HTTPStatus.OK
    assert response.content == b'%PDF-1.4'


@pytest.mark.asyncio
async def test_estranho_nao_baixa_release(
    client, session, user, doc, stored, other_token
):
    url = stored('artigo.pdf')
    await attach_release(session, doc, user, url)

    response = client.get(url, headers=auth(other_token))

    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_autenticado_ve_icone(
    client, session, user, stored, other_token
):
    url = stored('foto.png')
    session.add(UserImage(user_id=user.id, type='ICON', file_path=url))
    await session.commit()

    response = client.get(url, headers=auth(other_token))

    assert response.status_code == HTTPStatus.OK


def test_arquivo_sem_dono_exige_admin(client, stored, token, admin_token):
    url = stored('sugestao.pdf')

    assert (
        client.get(url, headers=auth(token)).status_code
        == HTTPStatus.FORBIDDEN
    )
    assert (
        client.get(url, headers=auth(admin_token)).status_code == HTTPStatus.OK
    )


def test_caminho_fora_da_pasta_responde_404(client, uploads, admin_token):
    (uploads.parent / 'segredo.txt').write_text('x')

    response = client.get(
        '/uploads/..%2Fsegredo.txt', headers=auth(admin_token)
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
