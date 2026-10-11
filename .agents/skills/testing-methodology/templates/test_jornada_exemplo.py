"""Jornada: <objetivo do usuário> (<spec e história de origem>).

<Descrição da jornada em prosa, a partir de templates/jornada.md: atores,
estado inicial, passos com o que cada ator espera ver e o desfecho.>

Exemplo genérico. Adapte os helpers e as rotas à aplicação; no pi*VMA, veja
references/06-projeto-pivma.md.
"""

from http import HTTPStatus

import pytest

# Helpers com nome de ação do usuário. Eles conferem o status esperado da
# própria ação; a jornada confere o comportamento.
from tests.journeys.helpers import (  # ajuste ao projeto
    bootstrap_fresh_environment,
    log_in,
    log_out,
    sign_up,
)


@pytest.mark.asyncio
async def test_revisor_pede_ajuste_e_autor_reenvia(client, session):
    # Estado inicial: ambiente novo, com o provisionamento real.
    await bootstrap_fresh_environment(session)
    sign_up(client, 'autor')
    sign_up(client, 'revisor')
    # ... conceder o papel de revisor pela interface, como o administrador

    # 1. O autor envia o documento e o vê como "em revisão".
    log_in(client, 'autor')
    doc = client.post('/documents', json={'title': 'V1'})
    assert doc.status_code == HTTPStatus.CREATED, doc.text
    doc_id = doc.json()['id']
    assert client.get(f'/documents/{doc_id}').json()['status'] == 'IN_REVIEW'
    log_out(client)

    # 2. O revisor encontra a pendência e pede ajuste com justificativa.
    log_in(client, 'revisor')
    pending = client.get('/tasks', params={'status': 'READY'}).json()['data']
    assert [t['document_id'] for t in pending] == [doc_id]
    decision = client.post(
        f'/documents/{doc_id}/review',
        json={'outcome': 'NEEDS_CHANGES', 'justification': 'Falta a fonte.'},
    )
    assert decision.status_code == HTTPStatus.OK, decision.text
    log_out(client)

    # 3. O autor lê a justificativa e reenvia; o revisor ainda não vê a
    #    versão nova até o envio.
    log_in(client, 'autor')
    current = client.get(f'/documents/{doc_id}').json()
    assert current['review']['justification'] == 'Falta a fonte.'
    resent = client.put(f'/documents/{doc_id}', json={'title': 'V2'})
    assert resent.status_code == HTTPStatus.OK, resent.text
    log_out(client)

    # 4. Desfecho: o revisor aprova a nova versão e a pendência some.
    log_in(client, 'revisor')
    approved = client.post(
        f'/documents/{doc_id}/review', json={'outcome': 'APPROVED'}
    )
    assert approved.status_code == HTTPStatus.OK, approved.text
    assert (
        client.get('/tasks', params={'status': 'READY'}).json()['data'] == []
    )
