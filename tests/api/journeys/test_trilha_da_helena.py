"""Jornada: a configuradora monta a trilha de estudo do grupo TCC.

Fonte: openspec/changes/study-guide (specs document-groups e study-guide,
decisão 7 do design.md).

Atores: Helena, coordenadora que configura o grupo de documentos "TCC".

Estado inicial: ambiente sem grupos. O Crossref responde por um substituto
que conhece só o artigo "Saúde coletiva e pesquisa" e conta as consultas.

Passos:
1. Helena cria o grupo TCC com outro documento, TCC e anteprojeto, nessa
   ordem, e vê os itens na ordem em que os criou.
2. Ela reordena para anteprojeto, TCC e outro documento e vê a nova ordem.
3. No anteprojeto, anexa a tipificação "Artigo científico" e vê o nome dela.
4. Cola um DOI com https://doi.org/ e letras maiúsculas. Vê o DOI limpo, com
   título, autores e ano vindos do Crossref.
5. Cola um segundo DOI, que o Crossref não responde. Vê o anexo salvo com o
   título que digitou e a origem dos metadados como manual.
6. Anexa um livro por link, com título.
7. Escreve uma descrição em cada anexo. O Crossref não é consultado de novo.
8. Reordena para o artigo introdutório vir primeiro.
9. Exclui o livro, que não fazia sentido no anteprojeto.

Desfecho: a lista do anteprojeto mostra artigo introdutório, tipificação e
artigo do Crossref, nessa ordem, com as descrições, e sem o livro.

Desvios (testados à parte, em tests/api/check_tree/):
- tipificação repetida (409), link sem título ou ftp (422), DOI repetido com
  outra escrita (409): test_study_attachments_api.py;
- lista de reordenação inválida (422): test_document_groups_api.py e
  test_study_attachments_api.py.
"""

from http import HTTPStatus

from lumina.services.crossref_client import DoiMetadata
import pytest

from tests.api.journeys.helpers import (
    attach,
    create_group,
    create_typification,
    log_in,
    make_admin,
    sign_up,
)


@pytest.mark.asyncio
async def test_coordenadora_monta_a_trilha_do_anteprojeto(
    client, session, crossref
):
    crossref.works['10.1590/s0102-311x2023000100001'] = DoiMetadata(
        title='Saúde coletiva e pesquisa',
        authors=['Ana Souza', 'Bruno Lima'],
        year=2023,
        container_title='Cadernos de Saúde Pública',
    )
    await make_admin(session, sign_up(client, 'helena'))
    helena = log_in(client, 'helena')

    # 1. Helena cria o grupo com os itens fora da ordem de trabalho.
    group, items = create_group(
        client, helena, 'TCC', ['Outro documento', 'TCC', 'Anteprojeto']
    )
    outro, tcc, anteprojeto = (item['id'] for item in items)
    listed = client.get(f'/document-group/{group["id"]}/items', headers=helena)
    assert [i['name'] for i in listed.json()] == [
        'Outro documento',
        'TCC',
        'Anteprojeto',
    ]

    # 2. Ela põe os itens na ordem em que o aluno vai trabalhar.
    reordered = client.put(
        f'/document-group/{group["id"]}/items/order',
        headers=helena,
        json={'item_ids': [anteprojeto, tcc, outro]},
    )
    assert reordered.status_code == HTTPStatus.OK, reordered.text
    assert [i['name'] for i in reordered.json()['items']] == [
        'Anteprojeto',
        'TCC',
        'Outro documento',
    ]

    # 3. Ela anexa a tipificação ao anteprojeto.
    typification = create_typification(client, helena, 'Artigo científico')
    tipificacao = attach(
        client,
        helena,
        anteprojeto,
        kind='TYPIFICATION',
        typification_id=typification['id'],
    )
    assert tipificacao['typification']['name'] == 'Artigo científico'

    # 4. Ela cola o DOI como veio do site do artigo.
    artigo = attach(
        client,
        helena,
        anteprojeto,
        kind='DOI',
        doi='https://doi.org/10.1590/S0102-311X2023000100001',
    )
    assert artigo['doi'] == '10.1590/s0102-311x2023000100001'
    assert artigo['doi_url'] == (
        'https://doi.org/10.1590/s0102-311x2023000100001'
    )
    assert artigo['title'] == 'Saúde coletiva e pesquisa'
    assert artigo['authors'] == ['Ana Souza', 'Bruno Lima']
    assert artigo['year'] == 2023
    assert artigo['metadata_source'] == 'CROSSREF'

    # 5. O Crossref não responde pelo segundo DOI, e o anexo é salvo assim
    #    mesmo, com o título que ela digitou.
    introducao = attach(
        client,
        helena,
        anteprojeto,
        kind='DOI',
        doi='10.1234/introducao',
        title='Introdução à pesquisa em saúde',
    )
    assert introducao['title'] == 'Introdução à pesquisa em saúde'
    assert introducao['authors'] == []
    assert introducao['metadata_source'] == 'MANUAL'

    # 6. Ela anexa um livro por link.
    livro = attach(
        client,
        helena,
        anteprojeto,
        kind='LINK',
        title='Livro XPTO',
        url='https://editora.example/xpto',
    )
    assert livro['url'] == 'https://editora.example/xpto'

    # 7. Ela escreve uma descrição em cada anexo, sem nova consulta ao
    #    Crossref.
    calls_before = list(crossref.calls)
    descriptions = {
        tipificacao['id']: 'Confira os critérios antes de escrever',
        artigo['id']: 'Leia a seção de metodologia antes de escrever',
        introducao['id']: 'Comece por aqui',
        livro['id']: 'Capítulo 2',
    }
    for attachment in (tipificacao, artigo, introducao, livro):
        edited = client.put(
            '/document-group/attachment',
            headers=helena,
            json={
                'id': attachment['id'],
                'kind': attachment['kind'],
                'typification_id': (attachment['typification'] or {}).get(
                    'id'
                ),
                'doi': attachment['doi'],
                'title': attachment['title'],
                'url': attachment['url'],
                'description': descriptions[attachment['id']],
            },
        )
        assert edited.status_code == HTTPStatus.OK, edited.text
        assert edited.json()['description'] == descriptions[attachment['id']]
    assert crossref.calls == calls_before

    # 8. Ela põe o artigo introdutório em primeiro.
    order = [introducao['id'], tipificacao['id'], artigo['id'], livro['id']]
    reordered = client.put(
        f'/document-group/item/{anteprojeto}/attachments/order',
        headers=helena,
        json={'attachment_ids': order},
    )
    assert reordered.status_code == HTTPStatus.OK, reordered.text
    assert [a['id'] for a in reordered.json()] == order

    # 9. Ela exclui o livro e confere a lista final.
    deleted = client.delete(
        f'/document-group/attachment/{livro["id"]}', headers=helena
    )
    assert deleted.status_code == HTTPStatus.NO_CONTENT
    final = client.get(
        f'/document-group/item/{anteprojeto}/attachments', headers=helena
    ).json()
    assert [a['id'] for a in final] == order[:3]
    assert [a['description'] for a in final] == [
        'Comece por aqui',
        'Confira os critérios antes de escrever',
        'Leia a seção de metodologia antes de escrever',
    ]
