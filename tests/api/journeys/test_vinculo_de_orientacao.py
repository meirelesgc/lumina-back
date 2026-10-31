"""Jornadas do vínculo de orientação depois da revisão de permissões."""

from http import HTTPStatus

import pytest

from tests.api.journeys.helpers import log_in, make_admin, sign_up


@pytest.mark.asyncio
async def test_orientando_escolhe_orientador_e_encerra_o_vinculo(
    client, session
):
    # 1. A orientadora e a aluna têm contas.
    marta = sign_up(client, 'marta')
    await make_admin(session, marta)
    bia = sign_up(client, 'bia')
    bia_headers = log_in(client, 'bia')

    # 2. A aluna vê a orientadora na lista, sem o telefone dela.
    advisors = client.get('/advisorship/advisors', headers=bia_headers).json()[
        'advisors'
    ]
    assert [a['id'] for a in advisors] == [marta['id']]
    assert 'phone_number' not in advisors[0]

    # 3. A aluna escolhe a orientadora.
    created = client.post(
        '/advisorship',
        headers=bia_headers,
        json={'advisor_id': marta['id'], 'advisee_id': bia['id']},
    )
    assert created.status_code == HTTPStatus.CREATED, created.text

    # 4. A aluna encerra o vínculo, e ele some da lista dela.
    closed = client.delete(
        f'/advisorship/{created.json()["id"]}', headers=bia_headers
    )
    assert closed.status_code == HTTPStatus.OK, closed.text
    my_advisors = client.get(
        '/advisorship/my-advisors', headers=bia_headers
    ).json()['advisors']
    assert my_advisors == []


@pytest.mark.asyncio
async def test_convite_aceito_reativa_vinculo_cancelado(client, session):
    # 1. O orientador e o aluno têm um vínculo ativo.
    rui = sign_up(client, 'rui')
    await make_admin(session, rui)
    rui_headers = log_in(client, 'rui')
    caio = sign_up(client, 'caio')
    caio_headers = log_in(client, 'caio')
    link = client.post(
        '/advisorship',
        headers=caio_headers,
        json={'advisor_id': rui['id'], 'advisee_id': caio['id']},
    ).json()

    # 2. O orientador cancela o vínculo.
    cancelled = client.put(
        f'/advisorship/{link["id"]}',
        headers=rui_headers,
        json={'status': 'CANCELLED'},
    )
    assert cancelled.status_code == HTTPStatus.OK, cancelled.text

    # 3. O orientador convida de novo, e o aluno aceita.
    invite = client.post(
        '/invitations',
        headers=rui_headers,
        json={'email': caio['email']},
    )
    assert invite.status_code == HTTPStatus.CREATED, invite.text
    accepted = client.post(
        f'/invitations/{invite.json()["token"]}/accept',
        headers=caio_headers,
    )
    assert accepted.status_code == HTTPStatus.OK, accepted.text

    # 4. O vínculo volta a valer para o aluno.
    my_advisors = client.get(
        '/advisorship/my-advisors',
        headers=caio_headers,
        params={'status': 'ACTIVE'},
    ).json()['advisors']
    assert [a['advisor']['id'] for a in my_advisors] == [rui['id']]
