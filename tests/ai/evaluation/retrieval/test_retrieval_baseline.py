"""
Jornada: o analista envia um anteprojeto para avaliação com uma árvore de
critérios e espera que o parecer de cada critério se apoie nos trechos do
documento que tratam daquele critério, e não nos de um critério vizinho
(OpenSpec: retrieval-annotated-baseline).

O teste ingere os PDFs anotados pelo caminho de produção e recupera as
evidências de cada ramo de `<nome>.retrieval.yaml`, com embeddings reais.

- Evidência de outro documento é falha crítica: tolerância zero.
- Recall de trechos, acerto de seção e página, precisão entre ramos e
  acerto do roteamento são métricas sobre o acervo, com piso. O piso só
  sobe: quem melhorar a recuperação sobe o piso no mesmo commit.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest
import pytest_asyncio
from langchain_core.documents import Document
from langchain_postgres import PGVector
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.schemas.branch import SectionRequirementScope
from lumina.services.ai.stages import retrieval
from tests.ai.evaluation.support import branch_query, document_filter
from tests.fixtures.answer_keys import (
    RETRIEVAL_KEYS,
    chunk_text,
    doc_id,
    expected_branches,
    is_annotated_place,
    normalize,
)

pytestmark = [pytest.mark.ai, pytest.mark.asyncio(loop_scope='session')]

MIN_EVIDENCE_RECALL = 0.54
MIN_SECTION_PAGE_HIT_RATE = 0.55
MIN_BRANCH_PRECISION = 0.20
MIN_ROUTING_HIT_RATE = 0.0

NOT_ROUTED = 'não roteado'


@dataclass
class BranchResult:
    branch: dict
    blocks: list[Document]
    candidates: Optional[list[str]] | str

    @property
    def evidence(self) -> list[dict]:
        return self.branch['evidence']

    @property
    def counts_for_routing(self) -> bool:
        requirement = self.branch.get('section_requirement') or {}
        return requirement.get(
            'scope'
        ) == SectionRequirementScope.SPECIFIC_SECTION.value and any(
            e.get('section') for e in self.evidence
        )


@dataclass
class DocumentResult:
    source: str
    branches: list[BranchResult]


async def retrieve_branches(
    session: AsyncSession, vstore: PGVector, retrieval_key: Path
) -> DocumentResult:
    base_filter = document_filter(retrieval_key)
    route = retrieval.route_candidate_sections
    routed: list = []

    async def route_spy(*args, **kwargs):
        candidates = await route(*args, **kwargs)
        routed.append(candidates)
        return candidates

    results = []
    with patch.object(retrieval, 'route_candidate_sections', route_spy):
        for taxonomy, branch in expected_branches(retrieval_key):
            routed.clear()
            payload = await retrieval.retrieve_criteria_payload(
                session,
                vstore,
                *branch_query(taxonomy, branch),
                base_filter,
                expansions=branch.get('expansions'),
                section_requirement=branch.get('section_requirement'),
            )
            results.append(
                BranchResult(
                    branch=branch,
                    blocks=payload['_chunks'],
                    candidates=routed[-1] if routed else NOT_ROUTED,
                )
            )
    return DocumentResult(source=base_filter['source'], branches=results)


@pytest_asyncio.fixture(scope='session', loop_scope='session')
async def retrieval_results(
    engine, indexed_vectorstore
) -> dict[str, DocumentResult]:
    """Recupera as evidências de todos os ramos uma vez por sessão."""
    async with AsyncSession(engine) as session:
        return {
            doc_id(key): await retrieve_branches(
                session, indexed_vectorstore, key
            )
            for key in RETRIEVAL_KEYS
        }


def own_snippets(result: BranchResult) -> list[str]:
    return [normalize(e['contains']) for e in result.evidence]


def classify_block(block: Document, own: list[str], others: list[str]) -> str:
    text = chunk_text(block.page_content)
    if any(snippet in text for snippet in own):
        return 'own'
    if any(snippet in text for snippet in others):
        return 'other'
    return 'unannotated'


def score_branch(result: BranchResult, doc: DocumentResult) -> dict:
    own = own_snippets(result)
    others = [
        snippet
        for other in doc.branches
        if other is not result
        for snippet in own_snippets(other)
    ]
    texts = [chunk_text(block.page_content) for block in result.blocks]
    kinds = [classify_block(b, own, others) for b in result.blocks]
    candidates = result.candidates
    expected = {
        normalize(e['section']) for e in result.evidence if e.get('section')
    }
    return {
        'snippets': sum(any(s in t for t in texts) for s in own),
        'places': sum(
            any(is_annotated_place(b, e) for b in result.blocks)
            for e in result.evidence
        ),
        'evidence': len(result.evidence),
        'own': kinds.count('own'),
        'other': kinds.count('other'),
        'unannotated': kinds.count('unannotated'),
        'first_hit': next(
            (i for i, kind in enumerate(kinds, start=1) if kind == 'own'),
            None,
        ),
        'routing_hit': isinstance(candidates, list)
        and any(normalize(c) in expected for c in candidates),
        'kinds': kinds,
    }


BLOCK_LABELS = {
    'own': 'do ramo',
    'other': 'de outro ramo',
    'unannotated': 'sem anotação',
}


def blocks_report(result: BranchResult, kinds: list[str]) -> list[str]:
    return [
        f'    {rank}. p{block.metadata["page"] + 1} '
        f'{block.metadata.get("section_title")} [{BLOCK_LABELS[kind]}]'
        for rank, (block, kind) in enumerate(
            zip(result.blocks, kinds), start=1
        )
    ]


def branch_report(result: BranchResult, score: dict) -> list[str]:
    branch_id = result.branch['id']
    routing = f'roteamento: {result.candidates}'
    if not result.evidence:
        header = f'  {branch_id}: sem evidência anotada | {routing}'
        return [header, *blocks_report(result, score['kinds'])]
    if not result.counts_for_routing and result.candidates != NOT_ROUTED:
        routing += ' (fora do piso)'
    header = (
        f'  {branch_id}: trechos {score["snippets"]}/{score["evidence"]} '
        f'| seção e página {score["places"]}/{score["evidence"]} '
        f'| 1º bloco do ramo: {score["first_hit"] or "nenhum"} '
        f'| {routing}'
    )
    return [header, *blocks_report(result, score['kinds'])]


def rate(hits: int, total: int) -> Optional[float]:
    return hits / total if total else None


@pytest.mark.parametrize('retrieval_key', RETRIEVAL_KEYS, ids=doc_id)
async def test_evidencias_vem_do_proprio_documento(
    retrieval_results, retrieval_key
):
    doc = retrieval_results[doc_id(retrieval_key)]

    leaked = [
        (result.branch['id'], block.metadata.get('source'))
        for result in doc.branches
        for block in result.blocks
        if block.metadata.get('source') != doc.source
    ]

    assert not leaked, f'Evidências de outro documento: {leaked}'


async def test_recuperacao_atinge_os_pisos(retrieval_results):
    totals = dict.fromkeys(
        (
            'snippets',
            'places',
            'evidence',
            'own',
            'other',
            'routing_hits',
            'routing_cases',
        ),
        0,
    )
    lines = []
    for name, doc in retrieval_results.items():
        lines.append(name)
        for result in doc.branches:
            score = score_branch(result, doc)
            lines.extend(branch_report(result, score))
            if not result.evidence:
                continue
            for field in ('snippets', 'places', 'evidence', 'own', 'other'):
                totals[field] += score[field]
            if result.counts_for_routing:
                totals['routing_cases'] += 1
                totals['routing_hits'] += score['routing_hit']

    metrics = {
        'Recall de trechos': (
            totals['snippets'],
            totals['evidence'],
            MIN_EVIDENCE_RECALL,
        ),
        'Acerto de seção e página': (
            totals['places'],
            totals['evidence'],
            MIN_SECTION_PAGE_HIT_RATE,
        ),
        'Precisão entre ramos': (
            totals['own'],
            totals['own'] + totals['other'],
            MIN_BRANCH_PRECISION,
        ),
        'Acerto do roteamento': (
            totals['routing_hits'],
            totals['routing_cases'],
            MIN_ROUTING_HIT_RATE,
        ),
    }
    below = []
    lines.append('Total')
    for metric, (hits, total, floor) in metrics.items():
        value = rate(hits, total)
        if value is None:
            lines.append(f'  {metric}: sem casos')
            continue
        lines.append(
            f'  {metric}: {hits}/{total} = {value:.2f} (piso {floor})'
        )
        if value < floor:
            below.append(metric)
    report = '\n'.join(lines)
    print(f'\nRecuperação sobre o acervo anotado\n{report}')

    assert not below, f'Abaixo do piso: {below}\n{report}'
