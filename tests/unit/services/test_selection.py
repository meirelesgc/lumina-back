"""
Jornada: o analista envia um documento para avaliação e espera que o parecer
de cada critério se apoie nas seções que tratam dele. O seletor lê o sumário,
pede seções pelo id, decide se basta e pode concluir que o conteúdo não
existe; nesse caso, o critério recebe "não contempla" sem chamar o avaliador
(OpenSpec: outline-section-selection).
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from langchain_core.documents import Document

from lumina.services.ai.stages.evaluation import evaluate_criteria_batch
from lumina.services.ai.stages.outline import build_outline, outline_markdown
from lumina.services.ai.stages.selection import (
    MAX_ROUNDS,
    SelectionOutcome,
    SelectionStep,
    select_evaluation_payloads,
    select_sections,
)

TAXONOMY = {'title': 'Fundamentação', 'sources': []}
BRANCH = {
    'id': 'objetivo-geral',
    'title': 'Objetivo geral',
    'description': 'O objetivo geral está definido?',
}
SPECIFIC = {'scope': 'SPECIFIC_SECTION', 'expected_section': 'Objetivos'}
ENTIRE = {'scope': 'ENTIRE_DOCUMENT', 'expected_section': None}
TITLES = ['1. Introdução', '2. Objetivos', '3. Metodologia']


class FakeSelector:
    """Modelo falso com saída estruturada: devolve as rodadas na ordem."""

    model_name = 'seletor-falso'

    def __init__(self, *steps):
        self.steps = list(steps)
        self.prompts: list[str] = []

    def with_structured_output(self, schema):
        assert schema is SelectionStep
        return self

    async def ainvoke(self, prompt):
        self.prompts.append(prompt)
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def step(*ids, enough=False, not_found=False, reason='motivo'):
    return SelectionStep(
        section_ids=list(ids),
        reason=reason,
        enough=enough,
        not_found=not_found,
    )


def outline():
    chunks = [
        Document(
            page_content=f'[{title}] Texto da seção {title}.',
            metadata={
                'section_index': index,
                'section_title': title,
                'section_path': title,
                'page': index,
                'chunk_index_in_section': 0,
                'chunk_id': f'chunk_{index}_0',
            },
        )
        for index, title in enumerate(TITLES)
    ]
    return build_outline(chunks)


async def select(model, requirement=SPECIFIC):
    return await select_sections(
        model, outline(), TAXONOMY, BRANCH, requirement
    )


@pytest.mark.asyncio
async def test_para_quando_o_seletor_diz_que_basta():
    model = FakeSelector(step('s02'), step(enough=True))

    selection = await select(model)

    assert selection.outcome == SelectionOutcome.SELECTED
    assert selection.section_ids == ['s02']
    assert len(selection.rounds) == 2  # noqa: PLR2004


@pytest.mark.asyncio
async def test_para_no_teto_de_rodadas_com_as_secoes_lidas():
    model = FakeSelector(step('s01'), step('s02'), step('s03'))

    selection = await select(model)

    assert len(selection.rounds) == MAX_ROUNDS
    assert selection.section_ids == ['s01', 's02', 's03']
    assert not model.steps


@pytest.mark.asyncio
async def test_para_quando_nao_ha_id_novo():
    model = FakeSelector(step('s01'), step('s01'))

    selection = await select(model)

    assert selection.outcome == SelectionOutcome.SELECTED
    assert selection.section_ids == ['s01']


@pytest.mark.asyncio
async def test_ignora_e_registra_ids_invalidos():
    model = FakeSelector(step('s01', 's99'), step(enough=True))

    selection = await select(model)

    assert selection.section_ids == ['s01']
    assert selection.rounds[0]['invalid'] == ['s99']


@pytest.mark.asyncio
async def test_ignora_nao_existe_na_primeira_rodada():
    model = FakeSelector(step('s03', not_found=True), step(enough=True))

    selection = await select(model)

    assert selection.outcome == SelectionOutcome.SELECTED
    assert selection.section_ids == ['s03']


@pytest.mark.asyncio
async def test_primeira_rodada_sem_id_valido_manda_o_documento_inteiro():
    model = FakeSelector(step('s42', not_found=True))

    selection = await select(model)

    assert selection.outcome == SelectionOutcome.FALLBACK
    assert selection.section_ids == ['s01', 's02', 's03']


@pytest.mark.asyncio
async def test_documento_inteiro_nao_chama_o_seletor():
    model = FakeSelector()

    selection = await select(model, requirement=ENTIRE)

    assert selection.outcome == SelectionOutcome.ENTIRE_DOCUMENT
    assert selection.section_ids == ['s01', 's02', 's03']
    assert not model.prompts


@pytest.mark.asyncio
async def test_saida_malformada_cai_no_documento_inteiro():
    model = FakeSelector(*[ValueError('saída fora do schema')] * 3)

    selection = await select(model)

    assert selection.outcome == SelectionOutcome.FALLBACK
    assert selection.section_ids == ['s01', 's02', 's03']
    assert 'saída fora do schema' in selection.error
    assert len(model.prompts) == 3  # noqa: PLR2004


@pytest.mark.asyncio
async def test_prompt_traz_o_sumario_e_a_dica_de_secao():
    model = FakeSelector(step('s02'), step(enough=True))

    await select(model)

    assert outline_markdown(outline()) in model.prompts[0]
    assert SPECIFIC['expected_section'] in model.prompts[0]
    assert 'Texto da seção 2. Objetivos.' in model.prompts[1]


def tree():
    now = '2026-10-17T00:00:00'
    typification_id, taxonomy_id = str(uuid4()), str(uuid4())
    return [
        {
            'id': typification_id,
            'name': 'Revisão',
            'sources': [],
            'created_at': now,
            'taxonomies': [
                {
                    'id': taxonomy_id,
                    'typification_id': typification_id,
                    'title': TAXONOMY['title'],
                    'description': 'Fundamentação da revisão',
                    'created_at': now,
                    'sources': [],
                    'branches': [
                        {
                            'id': str(uuid4()),
                            'taxonomy_id': taxonomy_id,
                            'title': BRANCH['title'],
                            'description': BRANCH['description'],
                            'section_scope': SPECIFIC['scope'],
                            'expected_section': SPECIFIC['expected_section'],
                            'created_at': now,
                        }
                    ],
                }
            ],
        }
    ]


async def payload_for(model):
    payloads = await select_evaluation_payloads(tree(), outline(), model)
    return payloads[0]


@pytest.mark.asyncio
async def test_payload_tem_o_que_a_avaliacao_le():
    payload = await payload_for(FakeSelector(step('s02'), step(enough=True)))

    assert '[FONTE] chunk_id: chunk_1_0' in payload['document']
    assert [c.metadata['chunk_id'] for c in payload['_chunks']] == [
        'chunk_1_0'
    ]
    assert 'Objetivo geral' in payload['requirement']
    assert payload['expected_section'] == TAXONOMY['title']
    assert 'section_requirement_version' not in payload
    assert payload['context_selection']['outcome'] == 'selected'
    assert payload['context_selection']['scope'] == SPECIFIC['scope']
    assert (
        payload['context_selection']['expected_section']
        == SPECIFIC['expected_section']
    )
    assert not payload.get('skip_evaluation')


@pytest.mark.asyncio
async def test_conteudo_inexistente_gera_nao_contempla_sem_avaliador():
    payload = await payload_for(
        FakeSelector(step('s01'), step(not_found=True))
    )

    assert payload['skip_evaluation'] is True
    assert payload['fulfilled'] is False
    assert payload['score'] == 0
    assert payload['references'] == []
    assert '1. Introdução' in payload['feedback']
    assert payload['context_selection']['outcome'] == 'not_found'


@pytest.mark.asyncio
async def test_avaliacao_pula_itens_sem_avaliador():
    chain = MagicMock()
    chain.abatch = AsyncMock(return_value=[{'fulfilled': True, 'score': 8}])
    skipped = {'id': 'a', 'skip_evaluation': True, 'fulfilled': False}
    evaluated = {'id': 'b', '_chunks': []}

    await evaluate_criteria_batch(chain, [skipped, evaluated])

    sent = chain.abatch.await_args.args[0]
    assert sent == [evaluated]
    assert skipped['fulfilled'] is False
    assert evaluated['fulfilled'] is True
