"""
Jornada: o analista envia uma revisão sistemática com subseções numeradas e
espera que a avaliação de um critério encontre trechos de qualquer subseção.
A recuperação só enxerga o texto que virou chunk, então estes testes
verificam a extração contra os gabaritos de `tests/fixtures/documents/`
(OpenSpec: ingest-subsections).

- Texto perdido é falha crítica: tolerância zero, por documento.
- Identificação de seções (título e página) é métrica sobre o acervo, com
  piso. Quem melhorar a detecção de títulos sobe o piso no mesmo commit.
"""

from pathlib import Path

import pytest

from tests.fixtures.answer_keys import (
    SECTIONS_KEYS,
    chunk_text,
    doc_id,
    expected_sections,
    extract,
    normalize,
    pdf_for,
)

MIN_SECTION_IDENTIFICATION_RATE = 1.0


@pytest.mark.parametrize('answer_key', SECTIONS_KEYS, ids=doc_id)
def test_texto_de_cada_secao_anotada_chega_aos_chunks(answer_key):
    chunks = extract(pdf_for(answer_key))
    text = ' '.join(chunk_text(c.page_content) for c in chunks)

    missing = [
        section['title']
        for section in expected_sections(answer_key)
        if section.get('starts_with')
        and normalize(section['starts_with']) not in text
    ]

    assert not missing, f'Seções sem texto nos chunks: {missing}'


def identified_sections(answer_key: Path) -> tuple[int, int]:
    """
    Conta as seções anotadas com título e primeira página corretos. Lê o
    caminho de títulos dos chunks: uma seção sem texto próprio, como
    "2. Desenvolvimento" logo antes de "2.1", não gera chunk, mas aparece
    no caminho dos chunks das filhas.
    """
    first_page: dict[str, int] = {}
    for chunk in extract(pdf_for(answer_key)):
        page = chunk.metadata['page'] + 1
        for title in chunk.metadata['section_path'].split(' > '):
            key = normalize(title)
            first_page[key] = min(first_page.get(key, page), page)

    sections = expected_sections(answer_key)
    hits = sum(
        first_page.get(normalize(section['title'])) == section['page']
        for section in sections
    )
    return hits, len(sections)


def test_identificacao_de_secoes_atinge_o_piso():
    scores = {doc_id(key): identified_sections(key) for key in SECTIONS_KEYS}
    hits = sum(hit for hit, _ in scores.values())
    total = sum(count for _, count in scores.values())
    report = '\n'.join(
        f'{doc}: {hit}/{count}' for doc, (hit, count) in scores.items()
    )
    print(f'\nIdentificação de seções\n{report}\nTotal: {hits}/{total}')

    assert hits / total >= MIN_SECTION_IDENTIFICATION_RATE, report
