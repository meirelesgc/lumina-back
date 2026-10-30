"""
Jornada: o analista abre a evidência de um critério e espera ver destacadas
só as frases que fundamentam o parecer. O teste compara as frases citadas
pelo modelo com os trechos anotados nos gabaritos `<nome>.retrieval.yaml`
(OpenSpec: sentence-level-citations).

O relatório mede a precisão do modelo e ainda não tem piso.
"""

import asyncio
from dataclasses import dataclass

import pytest
import pytest_asyncio
from langchain_core.callbacks import get_usage_metadata_callback

from lumina.core.llm import get_model
from lumina.services.ai.stages.evaluation import (
    evaluate_criteria_batch,
    get_evaluation_chain,
)
from lumina.services.ai.stages.selection import (
    SELECTION_CONCURRENCY,
    get_selector_model,
)
from tests.ai.evaluation.support import select_answer_key, usage_report
from tests.fixtures.answer_keys import RETRIEVAL_KEYS, doc_id, normalize

pytestmark = [pytest.mark.ai, pytest.mark.asyncio(loop_scope='session')]


@dataclass
class Row:
    branch_id: str
    citations: int
    by_sentence: int
    lines: int
    chunk_lines: int
    annotated: int
    found: int


def overlaps(snippet: str, annotated: str) -> bool:
    cited, expected = normalize(snippet), normalize(annotated)
    return bool(cited) and (cited in expected or expected in cited)


def row_for(branch: dict, payload: dict) -> Row:
    citations = payload.get('citations') or []
    references = payload.get('references') or []
    rects_by_chunk = {
        chunk.metadata['chunk_id']: len(chunk.metadata['rects'])
        for chunk in payload.get('_chunks') or []
    }
    snippets = [ref.get('text_snippet') or '' for ref in references]
    evidence = branch['evidence']
    return Row(
        branch_id=branch['id'],
        citations=len(citations),
        by_sentence=sum(bool(c.get('sentences')) for c in citations),
        lines=sum(len(ref['rects']) for ref in references),
        chunk_lines=sum(
            rects_by_chunk.get(ref['chunk_id'], 0) for ref in references
        ),
        annotated=len(evidence),
        found=sum(
            any(overlaps(snippet, item['contains']) for snippet in snippets)
            for item in evidence
        ),
    )


@pytest_asyncio.fixture(scope='session', loop_scope='session')
async def rows() -> tuple[dict[str, list[Row]], dict]:
    selector = get_selector_model()
    chain = get_evaluation_chain(await get_model())
    semaphore = asyncio.Semaphore(SELECTION_CONCURRENCY)
    selected = {
        doc_id(key): (await select_answer_key(key, selector, semaphore))[1]
        for key in RETRIEVAL_KEYS
    }
    with get_usage_metadata_callback() as usage:
        for pairs in selected.values():
            await evaluate_criteria_batch(
                chain, [payload for _, payload in pairs]
            )
    results = {
        name: [row_for(branch, payload) for branch, payload in pairs]
        for name, pairs in selected.items()
    }
    return results, usage.usage_metadata


def summary(label: str, rows_: list[Row]) -> str:
    citations = sum(r.citations for r in rows_)
    by_sentence = sum(r.by_sentence for r in rows_)
    lines = sum(r.lines for r in rows_)
    chunk_lines = sum(r.chunk_lines for r in rows_)
    annotated = sum(r.annotated for r in rows_)
    found = sum(r.found for r in rows_)
    return (
        f'{label}: citações por frase {by_sentence}/{citations} | '
        f'linhas destacadas {lines}/{chunk_lines} do chunk | '
        f'trechos anotados nas frases citadas {found}/{annotated}'
    )


async def test_relatorio_de_precisao_das_citacoes(rows):
    results, usage = rows
    lines = []
    for name, doc_rows in results.items():
        lines.append(summary(name, doc_rows))
        lines.extend(
            f'  {r.branch_id}: {r.found}/{r.annotated} trechos, '
            f'{r.lines}/{r.chunk_lines} linhas'
            for r in doc_rows
            if r.annotated
        )
    all_rows = [row for doc_rows in results.values() for row in doc_rows]
    lines.append(summary('Total', all_rows))
    lines.extend(usage_report(usage, 'Consumo do avaliador'))
    report = '\n'.join(lines)
    print(f'\nPrecisão das citações sobre o acervo anotado\n{report}')

    assert sum(r.by_sentence for r in all_rows) > 0, report
