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

    def with_structured_output(self, schema):
        return self

    async def ainvoke(self, prompt: str) -> SelectionStep:  # noqa: PLR6301
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
    set_fast_model_override(RuleSelector())
    yield
    set_fast_model_override(None)


async def persist(session, *entities):
    for entity in entities:
        session.add(entity)
    await session.commit()
    for entity in entities:
        await session.refresh(entity)


async def release_with_tree(session, user):
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
        BranchFactory(taxonomy_id=taxonomy.id, title=title)
        for title in (FOUND, MISSING)
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
