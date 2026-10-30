"""
Jornada: o analista clica em uma evidência e espera ver no PDF só as frases
que a fundamentam. Estes testes verificam as frases de cada chunk contra o
acervo de `tests/fixtures/documents/` (OpenSpec: sentence-level-citations).

Texto de chunk fora das frases é falha crítica: tolerância zero. A fração de
frases com retângulos e a redução de linhas são métricas com piso.
"""

import pytest

from tests.fixtures.answer_keys import (
    SECTIONS_KEYS,
    doc_id,
    extract,
    pdf_for,
)

MIN_SENTENCES_WITH_RECTS = 0.95
MAX_MEDIAN_LINES_RATIO = 0.3


def body_start(chunk) -> int:
    prefix = f'[{chunk.metadata.get("section_title", "")}] '
    return len(prefix) if chunk.page_content.startswith(prefix) else 0


def gaps(chunk) -> list[str]:
    """Texto do chunk que não pertence a nenhuma frase."""
    content = chunk.page_content
    cursor = body_start(chunk)
    found = []
    for sentence in chunk.metadata['sentences']:
        found.append(content[cursor : sentence['start']])
        cursor = sentence['end']
    found.append(content[cursor:])
    return [gap for gap in found if gap.strip()]


@pytest.mark.parametrize('answer_key', SECTIONS_KEYS, ids=doc_id)
def test_todo_texto_do_chunk_pertence_a_uma_frase(answer_key):
    chunks = extract(pdf_for(answer_key))

    failures = [
        f'{chunk.metadata["chunk_id"]}: {gap[:60]!r}'
        for chunk in chunks
        for gap in gaps(chunk)
    ]

    assert not failures, 'Texto fora das frases:\n' + '\n'.join(failures)


@pytest.mark.parametrize('answer_key', SECTIONS_KEYS, ids=doc_id)
def test_frases_seguem_a_ordem_e_a_numeracao(answer_key):
    for chunk in extract(pdf_for(answer_key)):
        sentences = chunk.metadata['sentences']
        assert sentences, chunk.metadata['chunk_id']
        assert [s['n'] for s in sentences] == list(
            range(1, len(sentences) + 1)
        )
        for left, right in zip(sentences, sentences[1:]):
            assert left['start'] < left['end'] <= right['start']


def score(answer_key) -> tuple[int, int, list[float]]:
    located = total = 0
    ratios = []
    for chunk in extract(pdf_for(answer_key)):
        chunk_lines = len(chunk.metadata['rects'])
        for sentence in chunk.metadata['sentences']:
            total += 1
            located += bool(sentence['rects'])
            if sentence['rects'] and chunk_lines:
                ratios.append(len(sentence['rects']) / chunk_lines)
    return located, total, ratios


def test_frases_atingem_os_pisos_de_posicao():
    located = total = 0
    ratios = []
    board = []
    for answer_key in SECTIONS_KEYS:
        doc_located, doc_total, doc_ratios = score(answer_key)
        located += doc_located
        total += doc_total
        ratios += doc_ratios
        board.append(f'{doc_id(answer_key)}: {doc_located}/{doc_total}')

    rate = located / total
    median = sorted(ratios)[len(ratios) // 2]
    print('\n'.join([*board, f'com retângulos {rate:.3f}, mediana {median}']))

    assert rate >= MIN_SENTENCES_WITH_RECTS, '\n'.join(board)
    assert median <= MAX_MEDIAN_LINES_RATIO, '\n'.join(board)
