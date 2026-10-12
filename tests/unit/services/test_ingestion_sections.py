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

import re
from functools import cache
from pathlib import Path

import pytest
import yaml

from lumina.services.ai.stages.extraction import extract_pdf_chunks

DOCUMENTS_DIR = Path(__file__).parents[2] / 'fixtures' / 'documents'
ANSWER_KEYS = sorted(DOCUMENTS_DIR.rglob('*.sections.yaml'))
ANSWER_KEY_SUFFIX = '.sections.yaml'

MIN_SECTION_IDENTIFICATION_RATE = 0.80

CHUNK_PREFIX = re.compile(r'^\[[^\]]*\]\s*')
HTML_TAG = re.compile(r'<[^>]+>')
MARKDOWN_MARK = re.compile(r'[*_#`]')


def normalize(text: str) -> str:
    """Remove a marcação do pymupdf4llm, junta espaços e ignora caixa."""
    text = MARKDOWN_MARK.sub('', HTML_TAG.sub(' ', text))
    return ' '.join(text.split()).casefold()


def expected_sections(answer_key: Path) -> list[dict]:
    data = yaml.safe_load(answer_key.read_text(encoding='utf-8'))
    sections = []
    for section in data['sections']:
        sections.append(section)
        sections.extend(section.get('subsections', []))
    return sections


@cache
def extract(answer_key: Path) -> list:
    stem = answer_key.name.removesuffix(ANSWER_KEY_SUFFIX)
    pdf = answer_key.with_name(f'{stem}.pdf')
    chunks, *_ = extract_pdf_chunks(str(pdf), pdf.name)
    return chunks


def doc_id(answer_key: Path) -> str:
    return str(answer_key.relative_to(DOCUMENTS_DIR))


@pytest.mark.parametrize('answer_key', ANSWER_KEYS, ids=doc_id)
def test_texto_de_cada_secao_anotada_chega_aos_chunks(answer_key):
    chunks = extract(answer_key)
    text = normalize(
        ' '.join(CHUNK_PREFIX.sub('', c.page_content) for c in chunks)
    )

    missing = [
        section['title']
        for section in expected_sections(answer_key)
        if section.get('starts_with')
        and normalize(section['starts_with']) not in text
    ]

    assert not missing, f'Seções sem texto nos chunks: {missing}'


def identified_sections(answer_key: Path) -> tuple[int, int]:
    """Conta as seções anotadas com título e primeira página corretos."""
    first_page: dict[int, tuple[str, int]] = {}
    for chunk in extract(answer_key):
        meta = chunk.metadata
        title = normalize(meta['section_title'])
        page = meta['page'] + 1
        current = first_page.get(meta['section_index'])
        if current is None or page < current[1]:
            first_page[meta['section_index']] = (title, page)

    found = set(first_page.values())
    sections = expected_sections(answer_key)
    hits = sum(
        (normalize(section['title']), section['page']) in found
        for section in sections
    )
    return hits, len(sections)


def test_identificacao_de_secoes_atinge_o_piso():
    scores = {doc_id(key): identified_sections(key) for key in ANSWER_KEYS}
    hits = sum(hit for hit, _ in scores.values())
    total = sum(count for _, count in scores.values())
    report = '\n'.join(
        f'{doc}: {hit}/{count}' for doc, (hit, count) in scores.items()
    )
    print(f'\nIdentificação de seções\n{report}\nTotal: {hits}/{total}')

    assert hits / total >= MIN_SECTION_IDENTIFICATION_RATE, report
