"""
Jornada: o analista envia o anteprojeto para avaliação contra uma árvore com
dois critérios. O seletor encontra a seção de um e conclui que o conteúdo do
outro não existe. Os dois critérios recebem veredito: o primeiro pelo
avaliador, o segundo como "não contempla" sem chamar o avaliador. Cada
veredito guarda a seleção que o gerou (OpenSpec: outline-section-selection).

Os modelos são falsos. A extração, a anonimização e o banco são reais; a
base vetorial é simulada.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_community.chat_models.fake import FakeListChatModel
from pydantic import Field
from sqlalchemy import select

from lumina.core.llm import set_fast_model_override
from lumina.models import (
    AppliedBranch,
    Document,
    DocumentHistory,
    DocumentRelease,
    DocumentTypification,
)
from lumina.schemas.document import DocumentProcessingStatus
from lumina.services.ai import pipeline
from lumina.services.ai.stages.extraction import extract_pdf_chunks
from lumina.services.ai.stages.selection import SelectionStep
from tests.factories.branch_factory import (
    BranchFactory,
    TaxonomyFactory,
    TypificationFactory,
)

PDF = (
    Path(__file__).parents[1]
    / 'fixtures'
    / 'documents'
    / 'research_proposal'
    / 'estrategias_teste_software_llm_judge_hitl.pdf'
)
FOUND = 'Objetivo geral'
MISSING = 'Cronograma'
VERDICT = json.dumps({
    'feedback': '**Veredito:** Atende.',
    'fulfilled': True,
    'score': 9,
    'citations': [],
})


class RecordingModel(FakeListChatModel):
    """Modelo falso que guarda os prompts recebidos."""

    prompts: list[str] = Field(default_factory=list)

    def _call(self, messages, *args, **kwargs):
        self.prompts.append(str(messages))
        return super()._call(messages, *args, **kwargs)

    def evaluator_prompts(self) -> list[str]:
        return [p for p in self.prompts if 'critério normativo' in p]


class RuleSelector:
    """
    Seletor falso que responde pelo critério do prompt: pede a primeira
    seção na primeira rodada e, na segunda, diz que basta ou que o conteúdo
    não existe.
    """

    model_name = 'seletor-falso'

    def __init__(self):
        self.prompts: list[str] = []

    def with_structured_output(self, schema):
        return self

    async def ainvoke(self, prompt: str) -> SelectionStep:
        self.prompts.append(prompt)
        first_round = 'Seções já lidas\nNenhuma.' in prompt
        missing = MISSING in prompt
        return SelectionStep(
            section_ids=['s01'] if first_round else [],
            reason='regra do teste',
            enough=not first_round and not missing,
            not_found=not first_round and missing,
        )


@pytest.fixture
def selector():
    rule_selector = RuleSelector()
    set_fast_model_override(rule_selector)
    yield rule_selector
    set_fast_model_override(None)


async def persist(session, *entities):
    for entity in entities:
        session.add(entity)
    await session.commit()
    for entity in entities:
        await session.refresh(entity)


async def release_with_tree(session, user, branches_kwargs=None):
    document = Document(
        name='Anteprojeto',
        identifier='ANT-1',
        description='Anteprojeto de TCC',
        processing_status=DocumentProcessingStatus.IDLE,
    )
    await persist(session, document)
    history = DocumentHistory(document_id=document.id, status='ACTIVE')
    await persist(session, history)
    release = DocumentRelease(history_id=history.id, file_path=str(PDF))
    typification = TypificationFactory()
    await persist(session, release, typification)
    taxonomy = TaxonomyFactory(typification_id=typification.id)
    await persist(session, taxonomy)
    branches = [
        BranchFactory(taxonomy_id=taxonomy.id, **kwargs)
        for kwargs in branches_kwargs
        or [{'title': FOUND}, {'title': MISSING}]
    ]
    link = DocumentTypification(
        document_id=document.id, typification_id=typification.id
    )
    for entity in (typification, taxonomy, *branches):
        entity.set_creation_audit(user.id)
    await persist(session, *branches, link)
    return release


@pytest.mark.asyncio
async def test_todo_criterio_recebe_veredito_com_a_selecao_gravada(
    session, user, selector
):
    release = await release_with_tree(session, user)
    model = RecordingModel(responses=[VERDICT, 'Síntese executiva.'])
    vstore = MagicMock(aadd_documents=AsyncMock())

    await pipeline.process_release_pipeline(
        session, release.id, model, vstore, AsyncMock()
    )

    applied = (await session.scalars(select(AppliedBranch))).all()
    by_title = {branch.title: branch for branch in applied}
    found, missing = by_title[FOUND], by_title[MISSING]

    assert found.fulfilled is True
    assert found.context_selection['outcome'] == 'selected'
    assert found.context_selection['section_ids'] == ['s01']
    assert missing.fulfilled is False
    assert missing.context_selection['outcome'] == 'not_found'
    assert 'Seções inspecionadas' in missing.feedback
    assert len(model.evaluator_prompts()) == 1
    assert FOUND in model.evaluator_prompts()[0]


@pytest.mark.asyncio
async def test_avaliacao_segue_a_marcacao_de_escopo_do_ramo(
    session, user, selector
):
    """
    Jornada: o configurador marcou um critério como documento inteiro e
    outro com a seção "Objetivos" (OpenSpec: manual-branch-section-scope).
    """
    whole = 'Redação clara'
    release = await release_with_tree(
        session,
        user,
        [
            {'title': whole, 'section_scope': 'ENTIRE_DOCUMENT'},
            {
                'title': FOUND,
                'section_scope': 'SPECIFIC_SECTION',
                'expected_section': 'Objetivos',
            },
        ],
    )
    model = RecordingModel(responses=[VERDICT, VERDICT, 'Síntese.'])
    vstore = MagicMock(aadd_documents=AsyncMock())

    await pipeline.process_release_pipeline(
        session, release.id, model, vstore, AsyncMock()
    )

    applied = (await session.scalars(select(AppliedBranch))).all()
    by_title = {branch.title: branch.context_selection for branch in applied}

    assert by_title[whole]['outcome'] == 'entire_document'
    assert by_title[whole]['scope'] == 'ENTIRE_DOCUMENT'
    assert by_title[whole]['expected_section'] is None
    assert by_title[FOUND]['scope'] == 'SPECIFIC_SECTION'
    assert by_title[FOUND]['expected_section'] == 'Objetivos'
    assert selector.prompts
    assert all(whole not in prompt for prompt in selector.prompts)
    assert all(
        'Seção esperada pelo analista: Objetivos' in prompt
        for prompt in selector.prompts
    )


def citable_chunk():
    """Chunk em que uma frase ocupa menos linhas que o chunk inteiro."""
    chunks, *_ = extract_pdf_chunks(str(PDF), 'fonte')
    return next(
        chunk
        for chunk in chunks
        if any(
            0 < len(sentence['rects']) < len(chunk.metadata['rects'])
            for sentence in chunk.metadata['sentences']
        )
    )


@pytest.mark.asyncio
async def test_analista_ve_destacada_so_a_frase_citada(
    session, user, selector
):
    """
    Jornada: o analista envia o anteprojeto e abre a evidência de um critério.
    O modelo cita uma frase, e a referência traz os retângulos dessa frase, em
    vez de todas as linhas do chunk (OpenSpec: sentence-level-citations).
    """
    chunk = citable_chunk()
    sentence = next(
        s
        for s in chunk.metadata['sentences']
        if 0 < len(s['rects']) < len(chunk.metadata['rects'])
    )
    verdict = json.dumps({
        'feedback': '**Veredito:** Atende.',
        'fulfilled': True,
        'score': 9,
        'citations': [
            {
                'chunk_id': chunk.metadata['chunk_id'],
                'sentences': [sentence['n']],
            }
        ],
    })
    release = await release_with_tree(
        session, user, [{'title': FOUND, 'section_scope': 'ENTIRE_DOCUMENT'}]
    )
    model = RecordingModel(responses=[verdict, 'Síntese.'])
    vstore = MagicMock(aadd_documents=AsyncMock())

    await pipeline.process_release_pipeline(
        session, release.id, model, vstore, AsyncMock()
    )

    [applied] = (await session.scalars(select(AppliedBranch))).all()
    [reference] = applied.references

    assert f'[s{sentence["n"]}]' in model.evaluator_prompts()[0]
    assert reference['chunk_id'] == chunk.metadata['chunk_id']
    assert reference['page'] == chunk.metadata['page']
    assert len(reference['rects']) == len(sentence['rects'])
    assert reference['text_snippet']
