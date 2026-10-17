"""
Consistência dos gabaritos `<nome>.retrieval.yaml` de
`tests/fixtures/documents/`, sem IA (OpenSpec: retrieval-annotated-baseline).

O placar da recuperação (`tests/ai/evaluation/retrieval/`) mede o motor
contra estes gabaritos. Um trecho anotado na página errada ou alterado pela
anonimização vira um erro que nenhuma melhoria da recuperação corrige, então
estas verificações têm tolerância zero.
"""

from pathlib import Path

import pytest

from lumina.schemas.branch import SectionRequirementScope
from tests.fixtures.answer_keys import (
    RETRIEVAL_KEYS,
    anonymized,
    chunk_text,
    doc_id,
    expected_branches,
    expected_sections,
    is_annotated_place,
    normalize,
    pdf_for,
    sections_key_for,
)

VALID_SCOPES = {scope.value for scope in SectionRequirementScope}


@pytest.mark.parametrize('retrieval_key', RETRIEVAL_KEYS, ids=doc_id)
def test_gabarito_de_recuperacao_tem_estrutura_valida(retrieval_key: Path):
    assert sections_key_for(retrieval_key).exists(), (
        f'{doc_id(retrieval_key)} sem gabarito de seções ao lado'
    )
    assert pdf_for(retrieval_key).exists(), (
        f'{doc_id(retrieval_key)} sem PDF ao lado'
    )

    ids = [branch['id'] for _, branch in expected_branches(retrieval_key)]
    duplicated = sorted({i for i in ids if ids.count(i) > 1})
    invalid = [
        (branch['id'], branch['section_requirement'].get('scope'))
        for _, branch in expected_branches(retrieval_key)
        if 'section_requirement' in branch
        and branch['section_requirement'].get('scope') not in VALID_SCOPES
    ]
    without_evidence = [
        branch['id']
        for _, branch in expected_branches(retrieval_key)
        if not isinstance(branch.get('evidence'), list)
    ]

    assert not duplicated, f'ids repetidos: {duplicated}'
    assert not invalid, f'scope inválido: {invalid}'
    assert not without_evidence, (
        f'ramos sem lista evidence: {without_evidence}'
    )


@pytest.mark.parametrize('retrieval_key', RETRIEVAL_KEYS, ids=doc_id)
def test_veredito_anotado_e_coerente_com_a_evidencia(retrieval_key: Path):
    """
    `fulfilled` é obrigatório nos ramos com evidência e, num ramo com
    `evidence: []`, só pode ser `false`.
    """
    branches = [branch for _, branch in expected_branches(retrieval_key)]

    not_bool = [
        branch['id']
        for branch in branches
        if 'fulfilled' in branch and not isinstance(branch['fulfilled'], bool)
    ]
    missing = [
        branch['id']
        for branch in branches
        if branch['evidence'] and 'fulfilled' not in branch
    ]
    contemplated_empty = [
        branch['id']
        for branch in branches
        if not branch['evidence'] and branch.get('fulfilled') is True
    ]

    assert not not_bool, f'fulfilled não booleano: {not_bool}'
    assert not missing, f'ramos com evidência sem fulfilled: {missing}'
    assert not contemplated_empty, (
        f'ramos sem evidência marcados como contemplados: {contemplated_empty}'
    )


@pytest.mark.parametrize('retrieval_key', RETRIEVAL_KEYS, ids=doc_id)
def test_secoes_anotadas_existem_no_gabarito_de_secoes(retrieval_key: Path):
    titles = {
        normalize(section['title'])
        for section in expected_sections(sections_key_for(retrieval_key))
    }

    unknown = [
        (branch['id'], evidence['section'])
        for _, branch in expected_branches(retrieval_key)
        for evidence in branch['evidence']
        if evidence.get('section')
        and normalize(evidence['section']) not in titles
    ]

    assert not unknown, (
        f'{doc_id(retrieval_key)}: seções fora do gabarito de seções: '
        f'{unknown}'
    )


@pytest.mark.parametrize('retrieval_key', RETRIEVAL_KEYS, ids=doc_id)
def test_trechos_anotados_estao_no_lugar_anotado(retrieval_key: Path):
    chunks = anonymized(pdf_for(retrieval_key))

    misplaced = []
    for _, branch in expected_branches(retrieval_key):
        for evidence in branch['evidence']:
            snippet = normalize(evidence['contains'])
            holders = [
                c for c in chunks if snippet in chunk_text(c.page_content)
            ]
            if any(is_annotated_place(c, evidence) for c in holders):
                continue
            found_at = sorted({
                (c.metadata['page'] + 1, c.metadata['section_path'])
                for c in holders
            })
            misplaced.append(
                f'{branch["id"]}: {evidence["contains"]!r} anotado em '
                f'{evidence.get("section")} p{evidence["page"]}, '
                f'encontrado em {found_at or "nenhum chunk"}'
            )

    assert not misplaced, f'{doc_id(retrieval_key)}:\n' + '\n'.join(misplaced)
