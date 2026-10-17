"""
Jornada: o analista envia um documento para avaliação e lê, para cada
critério da árvore, se o documento contempla ou não contempla o critério.
O teste compara o `fulfilled` da avaliação com o veredicto anotado nos
gabaritos `<nome>.retrieval.yaml` (OpenSpec: outline-section-selection).

Ramos com `evidence: []` esperam "não contempla". O acerto soma o acervo
inteiro e tem piso. O piso só sobe: quem melhorar a avaliação sobe o piso no
mesmo commit.
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
from tests.fixtures.answer_keys import (
    RETRIEVAL_KEYS,
    doc_id,
    expected_fulfilled,
)

pytestmark = [pytest.mark.ai, pytest.mark.asyncio(loop_scope='session')]

MIN_FULFILLED_ACCURACY = 0.78

SCHEMA_ERROR = 'Erro na validação de schema'


@dataclass
class Verdict:
    branch_id: str
    expected: bool
    fulfilled: bool
    schema_error: bool

    @property
    def hit(self) -> bool:
        return self.expected == self.fulfilled


def verdicts_for(pairs: list[tuple[dict, dict]]) -> list[Verdict]:
    return [
        Verdict(
            branch_id=branch['id'],
            expected=expected_fulfilled(branch),
            fulfilled=payload.get('fulfilled') is True,
            schema_error=SCHEMA_ERROR in str(payload.get('feedback')),
        )
        for branch, payload in pairs
    ]


@pytest_asyncio.fixture(scope='session', loop_scope='session')
async def verdicts() -> tuple[dict[str, list[Verdict]], dict, dict]:
    """
    Avalia cada ramo com o contexto escolhido pelo seletor de seções, como
    na produção: ramos que o seletor encerra como "não existe" já chegam
    com "não contempla" e não vão ao avaliador.
    """
    selector = get_selector_model()
    chain = get_evaluation_chain(await get_model())
    semaphore = asyncio.Semaphore(SELECTION_CONCURRENCY)
    with get_usage_metadata_callback() as selection_usage:
        selected = {
            doc_id(key): (await select_answer_key(key, selector, semaphore))[1]
            for key in RETRIEVAL_KEYS
        }
    with get_usage_metadata_callback() as evaluation_usage:
        for pairs in selected.values():
            await evaluate_criteria_batch(
                chain, [payload for _, payload in pairs]
            )
    results = {name: verdicts_for(pairs) for name, pairs in selected.items()}
    return (
        results,
        selection_usage.usage_metadata,
        evaluation_usage.usage_metadata,
    )


def document_report(name: str, rows: list[Verdict]) -> list[str]:
    def count(expected: bool, fulfilled: bool) -> int:
        return sum(
            r.expected is expected and r.fulfilled is fulfilled for r in rows
        )

    hits = sum(r.hit for r in rows)
    lines = [
        f'{name}: {hits}/{len(rows)} | contempla certo {count(True, True)}, '
        f'não contempla certo {count(False, False)}, '
        f'falso contempla {count(False, True)}, '
        f'falso não contempla {count(True, False)} | '
        f'erros de schema {sum(r.schema_error for r in rows)}'
    ]
    lines.extend(
        f'  errou {r.branch_id}: esperado '
        f'{"contempla" if r.expected else "não contempla"}'
        for r in rows
        if not r.hit
    )
    return lines


async def test_acerto_de_fulfilled_atinge_o_piso(verdicts):
    results, selection_usage, evaluation_usage = verdicts
    lines = []
    for name, rows in results.items():
        lines.extend(document_report(name, rows))
    rows = [row for doc_rows in results.values() for row in doc_rows]
    hits = sum(row.hit for row in rows)
    accuracy = hits / len(rows)
    lines.append(
        f'Total: {hits}/{len(rows)} = {accuracy:.2f} '
        f'(piso {MIN_FULFILLED_ACCURACY})'
    )
    lines.extend(usage_report(selection_usage, 'Consumo do seletor'))
    lines.extend(usage_report(evaluation_usage, 'Consumo do avaliador'))
    report = '\n'.join(lines)
    print(f'\nAcerto de fulfilled sobre o acervo anotado\n{report}')

    assert accuracy >= MIN_FULFILLED_ACCURACY, report
