import logging
import re
from typing import Any, Dict, List, Tuple

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


def extract_raw_markdown_and_pages(  # noqa: PLR0914
    full_path: str,
) -> Tuple[str, List[Dict[str, Any]], int, int, Any]:
    """
    Extrai markdown bruto e lista de chunks por pagina em memoria via
    pymupdf4llm. Garante page: int (0-based) e sanitizacao de bytes nulos.
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

    page_map: List[Dict[str, Any]] = []
    text_parts: List[str] = []
    current_line = 1
    current_char = 0
    null_bytes = 0
    ws_ops = 0

    for idx, chunk in enumerate(page_chunks):
        raw_text = chunk.get('text', '')
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
            }
            for b in chunk.get('page_boxes', [])
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
