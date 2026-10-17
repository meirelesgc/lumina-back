"""
Jornada: o analista envia um documento para avaliação e espera que o parecer
de cada critério se apoie nas seções que tratam dele, e que o critério sem
conteúdo no documento receba "não contempla" (OpenSpec:
outline-section-selection).

O teste roda o seletor de seções sobre os chunks anonimizados de cada
gabarito `<nome>.retrieval.yaml`, com o escopo e a dica de seção anotados, e
mede o contexto que chegaria ao avaliador:

- Recall de trechos: trechos anotados presentes no contexto enviado.
- Acerto de inexistência: ramos com `evidence: []` que o seletor encerra
  como "não existe".
- Segurança de inexistência: ramos com evidência que o seletor não encerra
  como "não existe" (um erro aqui vira "não contempla" sem avaliador).

Os pisos só sobem: quem melhorar a seleção sobe o piso no mesmo commit.
"""

import asyncio
from dataclasses import dataclass

import pytest
import pytest_asyncio
from langchain_core.callbacks import get_usage_metadata_callback

from lumina.services.ai.stages.outline import OutlineSection
from lumina.services.ai.stages.selection import (
    SELECTION_CONCURRENCY,
    SelectionOutcome,
    get_selector_model,
)
from tests.ai.evaluation.support import select_answer_key, usage_report
from tests.fixtures.answer_keys import (
    RETRIEVAL_KEYS,
    chunk_text,
    doc_id,
    normalize,
)

pytestmark = [pytest.mark.ai, pytest.mark.asyncio(loop_scope='session')]

MIN_SELECTION_RECALL = 0.86
MIN_NOT_FOUND_HIT_RATE = 0.46
MIN_NOT_FOUND_SAFETY = 0.85


@dataclass
class BranchSelection:
    branch: dict
    payload: dict

    @property
    def selection(self) -> dict:
        return self.payload['context_selection']

    @property
    def not_found(self) -> bool:
        return self.selection['outcome'] == SelectionOutcome.NOT_FOUND

    @property
    def context(self) -> str:
        return ' '.join(
            chunk_text(c.page_content) for c in self.payload['_chunks']
        )

    def snippets_found(self) -> int:
        context = self.context
        return sum(
            normalize(e['contains']) in context
            for e in self.branch['evidence']
        )


@dataclass
class DocumentSelection:
    outline: list[OutlineSection]
    branches: list[BranchSelection]

    @property
    def document_tokens(self) -> int:
        return sum(section.tokens for section in self.outline)


async def select_document(
    retrieval_key, model, semaphore
) -> DocumentSelection:
    outline, pairs = await select_answer_key(retrieval_key, model, semaphore)
    return DocumentSelection(
        outline=outline,
        branches=[
            BranchSelection(branch=branch, payload=payload)
            for branch, payload in pairs
        ],
    )


@pytest_asyncio.fixture(scope='session', loop_scope='session')
async def selections() -> tuple[dict[str, DocumentSelection], dict]:
    model = get_selector_model()
    semaphore = asyncio.Semaphore(SELECTION_CONCURRENCY)
    with get_usage_metadata_callback() as usage:
        results = {
            doc_id(key): await select_document(key, model, semaphore)
            for key in RETRIEVAL_KEYS
        }
    return results, usage.usage_metadata


def branch_report(result: BranchSelection) -> str:
    selection = result.selection
    evidence = result.branch['evidence']
    found = (
        f'trechos {result.snippets_found()}/{len(evidence)}'
        if evidence
        else 'sem evidência anotada'
    )
    return (
        f'  {result.branch["id"]}: {found} | {selection["outcome"]} | '
        f'seções {", ".join(selection["section_ids"]) or "nenhuma"} | '
        f'rodadas {len(selection["rounds"])} | ~{selection["tokens"]} tokens'
    )


def document_report(name: str, doc: DocumentSelection) -> list[str]:
    sent = sum(b.selection['tokens'] for b in doc.branches if not b.not_found)
    whole = doc.document_tokens * len(doc.branches)
    lines = [
        f'{name}: ~{sent} tokens enviados contra ~{whole} com o documento '
        f'inteiro em todos os ramos'
    ]
    lines.extend(branch_report(b) for b in doc.branches)
    return lines


def rate(hits: int, total: int) -> float | None:
    return hits / total if total else None


async def test_selecao_de_secoes_atinge_os_pisos(selections):
    results, usage = selections
    branches = [b for doc in results.values() for b in doc.branches]
    with_evidence = [b for b in branches if b.branch['evidence']]
    empty = [b for b in branches if not b.branch['evidence']]

    metrics = {
        'Recall de trechos': (
            sum(b.snippets_found() for b in with_evidence),
            sum(len(b.branch['evidence']) for b in with_evidence),
            MIN_SELECTION_RECALL,
        ),
        'Acerto de inexistência': (
            sum(b.not_found for b in empty),
            len(empty),
            MIN_NOT_FOUND_HIT_RATE,
        ),
        'Segurança de inexistência': (
            sum(not b.not_found for b in with_evidence),
            len(with_evidence),
            MIN_NOT_FOUND_SAFETY,
        ),
    }

    lines = []
    for name, doc in results.items():
        lines.extend(document_report(name, doc))
    lines.append('Total')
    below = []
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
    wrong = [b.branch['id'] for b in with_evidence if b.not_found]
    lines.append(f'  Inexistência com evidência anotada: {wrong or "nenhuma"}')
    lines.extend(usage_report(usage))
    report = '\n'.join(lines)
    print(f'\nSeleção de seções sobre o acervo anotado\n{report}')

    assert not below, f'Abaixo do piso: {below}\n{report}'
