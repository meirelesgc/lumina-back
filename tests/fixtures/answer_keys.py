"""
Leitura dos gabaritos de `tests/fixtures/documents/`: `<nome>.sections.yaml`
(seções esperadas) e `<nome>.retrieval.yaml` (árvore de critérios e trechos
esperados por ramo). Ver `tests/fixtures/documents/README.md`.
"""

import asyncio
import copy
import re
from functools import cache
from pathlib import Path

import yaml

from lumina.services.ai.stages.anonymization import anonymize_chunks
from lumina.services.ai.stages.extraction import extract_pdf_chunks

DOCUMENTS_DIR = Path(__file__).parent / 'documents'
SECTIONS_SUFFIX = '.sections.yaml'
RETRIEVAL_SUFFIX = '.retrieval.yaml'
SECTIONS_KEYS = sorted(DOCUMENTS_DIR.rglob(f'*{SECTIONS_SUFFIX}'))
RETRIEVAL_KEYS = sorted(DOCUMENTS_DIR.rglob(f'*{RETRIEVAL_SUFFIX}'))

CHUNK_PREFIX = re.compile(r'^\[[^\]]*\]\s*', re.MULTILINE)
HTML_TAG = re.compile(r'<[^>]+>')
MARKDOWN_MARK = re.compile(r'[*_#`]')
SPACE_BEFORE_PUNCTUATION = re.compile(r'\s+([:;,.!?])')


def normalize(text: str) -> str:
    """
    Remove a marcação do pymupdf4llm, junta espaços e ignora caixa. O
    pymupdf4llm separa a pontuação que segue um negrito (`**Objetivo** :`),
    então o espaço antes da pontuação também sai.
    """
    text = MARKDOWN_MARK.sub('', HTML_TAG.sub(' ', text))
    text = SPACE_BEFORE_PUNCTUATION.sub(r'\1', text)
    return ' '.join(text.split()).casefold()


def chunk_text(page_content: str) -> str:
    """
    Texto normalizado de um chunk sem os prefixos `[título]`. Um bloco com
    vizinhos unidos traz um prefixo no início de cada linha.
    """
    return normalize(CHUNK_PREFIX.sub('', page_content))


def section_titles(chunk) -> list[str]:
    return [
        normalize(title)
        for title in chunk.metadata['section_path'].split(' > ')
    ]


def is_annotated_place(chunk, evidence: dict) -> bool:
    """
    O chunk está na página da evidência e, quando a evidência informa a
    seção, essa seção está no caminho de títulos do chunk.
    """
    if chunk.metadata['page'] + 1 != evidence['page']:
        return False
    section = evidence.get('section')
    return section is None or normalize(section) in section_titles(chunk)


def doc_id(answer_key: Path) -> str:
    return str(answer_key.relative_to(DOCUMENTS_DIR))


def pdf_for(answer_key: Path) -> Path:
    for suffix in (SECTIONS_SUFFIX, RETRIEVAL_SUFFIX):
        if answer_key.name.endswith(suffix):
            stem = answer_key.name.removesuffix(suffix)
            return answer_key.with_name(f'{stem}.pdf')
    raise ValueError(f'Gabarito desconhecido: {answer_key}')


def sections_key_for(retrieval_key: Path) -> Path:
    return pdf_for(retrieval_key).with_suffix(SECTIONS_SUFFIX)


def expected_sections(answer_key: Path) -> list[dict]:
    data = yaml.safe_load(answer_key.read_text(encoding='utf-8'))
    sections = []
    for section in data['sections']:
        sections.append(section)
        sections.extend(section.get('subsections', []))
    return sections


def expected_branches(retrieval_key: Path) -> list[tuple[dict, dict]]:
    """Pares (taxonomia, ramo) da árvore do gabarito, em ordem de leitura."""
    data = yaml.safe_load(retrieval_key.read_text(encoding='utf-8'))
    return [
        (taxonomy, branch)
        for typification in data['tree']
        for taxonomy in typification['taxonomies']
        for branch in taxonomy['branches']
    ]


@cache
def extract(pdf: Path) -> list:
    chunks, *_ = extract_pdf_chunks(str(pdf), pdf.name)
    return chunks


@cache
def anonymized(pdf: Path) -> list:
    """Chunks como a recuperação os vê: extraídos e anonimizados."""
    return asyncio.run(anonymize_chunks(copy.deepcopy(extract(pdf))))
