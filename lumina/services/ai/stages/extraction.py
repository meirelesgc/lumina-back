import logging
import math
import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Set, Tuple

import fitz
import pymupdf4llm
from langchain_core.documents import Document

from lumina.core.settings import Settings
from lumina.services.ai.stages.audit import export_ingestion_audit
from lumina.services.ai.stages.chunking import create_chunks_from_sections
from lumina.services.ai.stages.positioning import enrich_chunks_with_line_rects
from lumina.services.ai.stages.sections import (
    build_sections_tree_from_markdown,
)

logger = logging.getLogger(__name__)
SETTINGS = Settings()

# Cabecalhos e rodapes corridos: caixas que se repetem no topo ou na base
LAYOUT_RUNNING_CLASSES = frozenset({'page-header', 'page-footer'})
RUNNING_BAND = 0.12
MIN_LAYOUT_RUNNING_PAGES = 2
MIN_TEXT_RUNNING_PAGES = 3
MIN_TEXT_RUNNING_RATIO = 0.3

_KEY_MARKUP_RE = re.compile(r'<[^>]+>|[*_`#|>\\]+')
_DIGITS_RE = re.compile(r'\d+')

BoxRef = Tuple[int, int]


def running_key(text: str) -> str:
    """
    Chave de comparacao de uma caixa: sem markup, digitos trocados por '#'
    (numero de pagina muda), espacos juntos e sem diferenca de caixa.
    """
    text = _KEY_MARKUP_RE.sub(' ', text)
    text = _DIGITS_RE.sub('#', text)
    return ' '.join(text.split()).casefold()


def _in_band(bbox: List[float], height: float) -> bool:
    center = (bbox[1] + bbox[3]) / 2 / height
    return center <= RUNNING_BAND or center >= 1 - RUNNING_BAND


def find_running_boxes(pages: List[Dict[str, Any]]) -> Set[BoxRef]:
    """
    Caixas (pagina, indice da caixa) que repetem cabecalho ou rodape.
    Cada pagina traz 'text' (markdown bruto), 'boxes' e 'height'.
    - page-header/page-footer: sai se a chave aparece em 2 paginas ou mais.
    - outra caixa na faixa do topo ou da base: sai se a chave aparece em
      3 paginas e em 30% delas; a primeira ocorrencia fica.
    """
    candidates: List[Tuple[BoxRef, str, bool]] = []
    pages_by_key: Dict[str, Set[int]] = defaultdict(set)

    for page_idx, page in enumerate(pages):
        height = page.get('height') or 0
        for box_idx, box in enumerate(page['boxes']):
            cls = box.get('class')
            if cls == 'picture':
                continue
            is_layout = cls in LAYOUT_RUNNING_CLASSES
            if not is_layout and not (
                height and _in_band(box['bbox'], height)
            ):
                continue
            key = running_key(page['text'][box['pos'][0] : box['pos'][1]])
            if not key:
                continue
            candidates.append(((page_idx, box_idx), key, is_layout))
            pages_by_key[key].add(page_idx)

    min_text_pages = max(
        MIN_TEXT_RUNNING_PAGES,
        math.ceil(MIN_TEXT_RUNNING_RATIO * len(pages)),
    )
    running: Set[BoxRef] = set()
    for (page_idx, box_idx), key, is_layout in candidates:
        key_pages = pages_by_key[key]
        if is_layout:
            if len(key_pages) >= MIN_LAYOUT_RUNNING_PAGES:
                running.add((page_idx, box_idx))
        elif len(key_pages) >= min_text_pages and page_idx != min(key_pages):
            running.add((page_idx, box_idx))
    return running


def mask_ranges(text: str, ranges: Iterable[Tuple[int, int]]) -> str:
    """
    Troca cada intervalo [inicio, fim) por quebras de linha do mesmo
    tamanho. Os deslocamentos do texto nao mudam, e o espaco que sobra
    nao se junta ao normalizar espacos e tabulacoes.
    """
    chars = list(text)
    for start, end in ranges:
        chars[start:end] = '\n' * (end - start)
    return ''.join(chars)


def extract_raw_markdown_and_pages(  # noqa: PLR0914
    full_path: str,
) -> Tuple[str, List[Dict[str, Any]], int, int, Any]:
    """
    Extrai markdown bruto e lista de chunks por pagina em memoria via
    pymupdf4llm. Garante page: int (0-based) e sanitizacao de bytes nulos.
    Apaga os cabecalhos e rodapes corridos no texto bruto de cada pagina,
    antes de juntar espacos, porque o 'pos' das caixas aponta para esse
    texto; as caixas apagadas saem com 'running': True no page_map.
    Retorna (full_markdown, page_map, null_bytes, ws_ops, doc_fitz).
    """
    doc = fitz.open(full_path)
    page_chunks = pymupdf4llm.to_markdown(
        full_path, page_chunks=True, use_ocr=False
    )
    page_sizes = [
        {
            'width': p.rect.width,
            'height': p.rect.height,
            'rotation': p.rotation,
        }
        for p in doc
    ]
    running = find_running_boxes([
        {
            'text': chunk.get('text', ''),
            'boxes': chunk.get('page_boxes', []),
            'height': page_sizes[idx]['height']
            if idx < len(page_sizes)
            else None,
        }
        for idx, chunk in enumerate(page_chunks)
    ])

    page_map: List[Dict[str, Any]] = []
    text_parts: List[str] = []
    current_line = 1
    current_char = 0
    null_bytes = 0
    ws_ops = 0

    for idx, chunk in enumerate(page_chunks):
        raw_boxes = chunk.get('page_boxes', [])
        raw_text = mask_ranges(
            chunk.get('text', ''),
            [
                tuple(raw_boxes[box_idx]['pos'])
                for page_idx, box_idx in running
                if page_idx == idx
            ],
        )
        if '\x00' in raw_text:
            null_bytes += raw_text.count('\x00')
            raw_text = raw_text.replace('\x00', '')

        cleaned_text = re.sub(r'[ \t]+', ' ', raw_text)
        if cleaned_text != raw_text:
            ws_ops += 1
        raw_text = cleaned_text

        page_num_0_based = idx
        lines = raw_text.splitlines()
        num_lines = len(lines)
        start_line = current_line
        end_line = current_line + max(0, num_lines - 1)

        size = page_sizes[idx] if idx < len(page_sizes) else {}
        boxes = [
            {
                'class': b.get('class', 'text'),
                'bbox': list(b.get('bbox', [0, 0, 0, 0])),
                'pos': list(b.get('pos', [0, 0])),
                'running': (idx, box_idx) in running,
            }
            for box_idx, b in enumerate(raw_boxes)
        ]

        page_map.append({
            'page': page_num_0_based,
            'start_line': start_line,
            'end_line': end_line,
            'char_count': len(raw_text),
            'char_start': current_char,
            'width': size.get('width'),
            'height': size.get('height'),
            'rotation': size.get('rotation', 0),
            'boxes': boxes,
        })

        text_parts.append(raw_text)
        current_line = end_line + 3
        current_char += len(raw_text) + 2

    full_markdown = '\n\n'.join(text_parts)
    return full_markdown, page_map, null_bytes, ws_ops, doc


def extract_pdf_chunks(
    full_path: str, source_name: str
) -> Tuple[List[Document], int, int, int]:
    """
    Executa os 4 estagios em memoria:
    1. Extração bruta de Markdown e caixas de pagina
    2. Arvore de secoes com 5 cleaners e papeis
    3. Fatiamento por secao e por pagina (monopagina)
    4. Refinamento de retangulos de linha fisica ([[x0, y0, x1, y1], ...])
    """
    full_markdown, page_map, null_bytes, ws_ops, doc = (
        extract_raw_markdown_and_pages(full_path)
    )
    try:
        pages_count = len(page_map)
        sections = build_sections_tree_from_markdown(full_markdown, page_map)
        chunks = create_chunks_from_sections(
            sections, page_map, full_markdown, source_name
        )
        enriched_chunks = enrich_chunks_with_line_rects(
            chunks, doc, page_map, full_markdown
        )
        if SETTINGS.DEBUG_INGESTION_AUDIT:
            try:
                export_ingestion_audit(
                    full_path=full_path,
                    source_name=source_name,
                    full_markdown=full_markdown,
                    page_map=page_map,
                    sections=sections,
                    chunks=enriched_chunks,
                )
            except Exception as audit_exc:
                logger.warning(
                    'Falha ao exportar auditoria de ingestão para %s: %s',
                    full_path,
                    audit_exc,
                )
        return enriched_chunks, pages_count, null_bytes, ws_ops
    finally:
        doc.close()
