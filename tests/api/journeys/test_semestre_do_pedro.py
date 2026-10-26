"""Jornada: o orientando estuda pelo guia e a orientadora acompanha.

Fonte: openspec/changes/study-guide (spec study-guide, requisitos "Guia de
estudo do projeto" e "Marcar anexo como estudado"; decisão 7 do design.md).

Atores:
- Helena, que configurou o grupo TCC;
- Pedro, orientando, dono de dois projetos do grupo;
- Marina, orientadora de Pedro.

Estado inicial: Helena montou o grupo TCC com anteprojeto, TCC e outro
documento, e seis anexos no total. O Crossref responde por um substituto que
não conhece nenhum DOI.

Passos:
1. Pedro cria dois projetos do grupo TCC.
2. Pedro abre o guia do primeiro e vê os três entregáveis em ordem, com os
   anexos, e o placar 0 de 6.
3. Ele marca o primeiro artigo como estudado e vê 1 de 6 e a data.
4. Ele marca de novo e nada muda.
5. Ele marca outro anexo, desmarca, e o placar volta a 1 de 6.
6. Ele abre o guia do segundo projeto e vê 0 de 6, com o primeiro artigo
   ainda não estudado.
7. Marina convida Pedro para a orientação e ele aceita.
8. Marina abre o guia do primeiro projeto de Pedro e vê 1 de 6. Ela tenta
   marcar um anexo e recebe 403.

Desfecho: o progresso de Pedro fica em 1 de 6 no primeiro projeto e em 0 de 6
no segundo, e Marina acompanha sem marcar nada.

Desvios (testados à parte, em tests/api/check_tree/test_study_guide_api.py):
terceiro sem acesso, projeto sem grupo, tipificação ou anexo excluídos depois
da marcação, admin que lê e não marca, projeto excluído, data original
preservada numa segunda marcação.
"""

from http import HTTPStatus

from tests.api.journeys.helpers import (
    accept_invitation,
    attach,
    create_group,
    create_project,
    create_typification,
    invite_advisee,
    log_in,
    sign_up,
)


def _configurar_grupo_tcc(client, helena):
    group, items = create_group(
        client, helena, 'TCC', ['Anteprojeto', 'TCC', 'Outro documento']
    )
    anteprojeto, tcc, outro = (item['id'] for item in items)
    artigo_cientifico = create_typification(
        client, helena, 'Artigo científico'
    )
    revisao = create_typification(client, helena, 'Revisão sistemática')
    attachments = [
        attach(
            client,
            helena,
            anteprojeto,
            kind='DOI',
            doi='10.1234/artigo-introdutorio',
            title='Artigo introdutório',
        ),
        attach(
            client,
            helena,
            anteprojeto,
            kind='TYPIFICATION',
            typification_id=artigo_cientifico['id'],
        ),
        attach(
            client,
            helena,
            tcc,
            kind='TYPIFICATION',
            typification_id=artigo_cientifico['id'],
        ),
        attach(client, helena, tcc, kind='DOI', doi='10.1234/artigo-z'),
        attach(
            client,
            helena,
            outro,
            kind='TYPIFICATION',
            typification_id=revisao['id'],
        ),
        attach(
            client,
            helena,
            outro,
            kind='LINK',
            title='Livro XPTO',
            url='https://editora.example/xpto',
        ),
    ]
    return group, attachments


def _guia(client, headers, project_id):
    response = client.get(
        f'/project/{project_id}/study-guide', headers=headers
    )
    assert response.status_code == HTTPStatus.OK, response.text
    return response.json()


def _anexo(guia, attachment_id):
    return next(
        anexo
        for item in guia['items']
        for anexo in item['attachments']
        if anexo['id'] == attachment_id
    )


def _marcar(client, headers, project_id, attachment_id, method='PUT'):
    return client.request(
        method,
        f'/project/{project_id}/study-guide/attachment/{attachment_id}/studied',
        headers=headers,
    )


def test_orientando_estuda_pelo_guia_e_orientadora_acompanha(client, crossref):
    for name in ('helena', 'pedro', 'marina'):
        sign_up(client, name)
    group, anexos = _configurar_grupo_tcc(client, log_in(client, 'helena'))
    artigo, outro_anexo = anexos[0]['id'], anexos[3]['id']

    # 1. Pedro cria dois projetos do grupo TCC.
    pedro = log_in(client, 'pedro')
    primeiro = create_project(client, pedro, 'TCC do Pedro', group['id'])
    segundo = create_project(client, pedro, 'Segundo TCC', group['id'])

    # 2. Pedro abre o guia do primeiro projeto.
    guia = _guia(client, pedro, primeiro['id'])
    assert [item['name'] for item in guia['items']] == [
        'Anteprojeto',
        'TCC',
        'Outro documento',
    ]
    assert [len(item['attachments']) for item in guia['items']] == [2, 2, 2]
    assert guia['items'][0]['attachments'][0]['title'] == (
        'Artigo introdutório'
    )
    assert (guia['studied_attachments'], guia['total_attachments']) == (0, 6)

    # 3. Ele marca o primeiro artigo como estudado.
    marcado = _marcar(client, pedro, primeiro['id'], artigo)
    assert marcado.status_code == HTTPStatus.OK, marcado.text
    guia = _guia(client, pedro, primeiro['id'])
    assert guia['studied_attachments'] == 1
    assert _anexo(guia, artigo)['studied'] is True
    data_original = _anexo(guia, artigo)['studied_at']
    assert data_original is not None

    # 4. Ele marca de novo e nada muda. A suíte roda numa transação só, em
    #    que now() não avança; a preservação da data tem teste focado.
    assert _marcar(client, pedro, primeiro['id'], artigo).status_code == (
        HTTPStatus.OK
    )
    guia = _guia(client, pedro, primeiro['id'])
    assert guia['studied_attachments'] == 1
    assert _anexo(guia, artigo)['studied_at'] == data_original

    # 5. Ele marca outro anexo e desmarca.
    _marcar(client, pedro, primeiro['id'], outro_anexo)
    assert _guia(client, pedro, primeiro['id'])['studied_attachments'] == 2
    desmarcado = _marcar(
        client, pedro, primeiro['id'], outro_anexo, method='DELETE'
    )
    assert desmarcado.status_code == HTTPStatus.OK, desmarcado.text
    assert _guia(client, pedro, primeiro['id'])['studied_attachments'] == 1

    # 6. O segundo projeto tem progresso próprio.
    guia_segundo = _guia(client, pedro, segundo['id'])
    assert guia_segundo['studied_attachments'] == 0
    assert _anexo(guia_segundo, artigo)['studied'] is False

    # 7. Marina convida Pedro para a orientação e ele aceita.
    marina = log_in(client, 'marina')
    convite = invite_advisee(client, marina, 'pedro@lumina.com.br')
    accept_invitation(client, log_in(client, 'pedro'), convite)

    # 8. Marina acompanha o guia de Pedro e não consegue marcar.
    marina = log_in(client, 'marina')
    guia_marina = _guia(client, marina, primeiro['id'])
    assert guia_marina['studied_attachments'] == 1
    assert _anexo(guia_marina, artigo)['studied'] is True
    tentativa = _marcar(client, marina, primeiro['id'], outro_anexo)
    assert tentativa.status_code == HTTPStatus.FORBIDDEN
    assert _guia(client, pedro, primeiro['id'])['studied_attachments'] == 1
