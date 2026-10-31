from http import HTTPStatus

import pytest

from lumina.models import AbntConformityResult, TemplateConformityResult


def auth(token):
    return {'Authorization': f'Bearer {token}'}


ROUTES = [
    ('/abnt', AbntConformityResult, {}),
    ('/templates', TemplateConformityResult, {}),
]


async def create_result(session, model, owner):
    record = model(doc_id='doc-1', file_path='artigo.pdf')
    record.set_creation_audit(owner.id)
    session.add(record)
    await session.commit()
    return record


@pytest.mark.asyncio
@pytest.mark.parametrize(('prefix', 'model', '_extra'), ROUTES)
async def test_outro_usuario_nao_alcanca_resultado(
    client, session, user, other_token, prefix, model, _extra
):
    record = await create_result(session, model, user)
    url = f'{prefix}/results/{record.id}'

    assert (
        client.get(url, headers=auth(other_token)).status_code
        == HTTPStatus.FORBIDDEN
    )
    assert (
        client.delete(url, headers=auth(other_token)).status_code
        == HTTPStatus.FORBIDDEN
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(('prefix', 'model', '_extra'), ROUTES)
async def test_listagem_traz_so_os_resultados_do_dono(
    client, session, user, token, other_token, prefix, model, _extra
):
    record = await create_result(session, model, user)

    mine = client.get(f'{prefix}/results', headers=auth(token)).json()
    other = client.get(f'{prefix}/results', headers=auth(other_token)).json()
    by_doc = client.get(
        f'{prefix}/doc-1/conformidade', headers=auth(other_token)
    ).json()

    assert [item['id'] for item in mine['results']] == [str(record.id)]
    assert other == {'count': 0, 'results': []}
    assert by_doc == {'count': 0, 'results': []}


@pytest.mark.asyncio
@pytest.mark.parametrize(('prefix', 'model', '_extra'), ROUTES)
async def test_admin_le_resultado_de_outro(
    client, session, user, admin_token, prefix, model, _extra
):
    record = await create_result(session, model, user)

    response = client.get(
        f'{prefix}/results/{record.id}', headers=auth(admin_token)
    )

    assert response.status_code == HTTPStatus.OK
