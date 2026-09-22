import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pymupdf
from langchain_core.documents import Document

from lumina.core.settings import Settings
from lumina.services.ai.stages.chunking import (
    documents_to_dict,
    documents_to_markdown_preview,
)
from lumina.services.ai.stages.positioning import (
    char_range_to_blocks,
    refine_block_to_line_rects,
)
from lumina.services.ai.stages.section_models import Section
from lumina.services.ai.stages.sections import (
    flatten_sections,
    tree_to_dict,
    tree_to_markdown,
)

logger = logging.getLogger(__name__)
SETTINGS = Settings()

CHUNK_COLORS = [
    (1.0, 0.85, 0.2),
    (0.5, 0.85, 1.0),
    (0.6, 1.0, 0.6),
    (1.0, 0.65, 0.85),
    (0.85, 0.7, 1.0),
    (1.0, 0.75, 0.5),
]

ROLE_COLORS = {
    'title_block': (0.5, 0.5, 0.5),
    'abstract': (0.1, 0.5, 0.9),
    'introduction': (0.1, 0.7, 0.3),
    'methodology': (0.9, 0.5, 0.0),
    'results': (0.6, 0.2, 0.8),
    'discussion': (0.9, 0.2, 0.5),
    'conclusion': (0.8, 0.1, 0.1),
    'references': (0.4, 0.3, 0.2),
    'unknown': (0.75, 0.75, 0.75),
}


RECT_COORDS_COUNT = 4


def annotate_pdf_document(  # noqa: PLR0913, PLR0914, PLR0917
    full_path: str,
    output_pdf_path: Path,
    full_markdown: str,
    page_map: List[Dict[str, Any]],
    sections: List[Section],
    chunks: List[Document],
) -> None:
    """
    Desenha barras marginais de seções e destaques translúcidos de chunks
    no PDF, salvando o resultado em output_pdf_path.
    """
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    with pymupdf.open(full_path) as pdf:
        cache: Dict[int, list] = {}

        def words_provider(page_idx: int) -> list:
            if page_idx not in cache:
                cache[page_idx] = (
                    pdf[page_idx].get_text('words')
                    if 0 <= page_idx < len(pdf)
                    else []
                )
            return cache[page_idx]

        # 1. Anotação de Seções (barras verticais na margem esquerda)
        for sec in flatten_sections(sections):
            sec_start = (
                sec.heading_char_start
                if sec.heading_char_start is not None
                else sec.char_start
            )
            sec_end = sec.char_end
            if sec_start is None or sec_end is None or sec_start >= sec_end:
                continue

            role_str = (
                sec.role.value
                if hasattr(sec.role, 'value')
                else str(sec.role or 'unknown')
            )
            color = ROLE_COLORS.get(role_str, ROLE_COLORS['unknown'])

            blocks = char_range_to_blocks(page_map, sec_start, sec_end)
            by_page: Dict[int, List[Any]] = {}

            for block in blocks:
                p_idx = block.get('page', 0)
                line_rects = refine_block_to_line_rects(
                    full_markdown,
                    block,
                    sec_start,
                    sec_end,
                    words_provider(p_idx),
                )
                if line_rects:
                    by_page.setdefault(p_idx, []).extend(line_rects)

            for page_no, rs in by_page.items():
                if 0 <= page_no < len(pdf) and rs:
                    page = pdf[page_no]
                    min_y = min(r[1] for r in rs)
                    max_y = max(r[3] for r in rs)
                    bar = pymupdf.Rect(4, min_y, 8, max_y)
                    page.draw_rect(bar, color=color, fill=color, width=0)
                    label = f'{role_str}: {sec.title}'[:40]
                    page.insert_text(
                        (10, min_y + 5), label, fontsize=4.5, color=color
                    )

        # 2. Anotação de Chunks (highlights translúcidos por linha)
        for i, chunk in enumerate(chunks):
            meta = chunk.metadata
            chunk_page = meta.get('page')
            rects = meta.get('rects', [])
            if chunk_page is not None and 0 <= chunk_page < len(pdf) and rects:
                page = pdf[chunk_page]
                color = CHUNK_COLORS[i % len(CHUNK_COLORS)]
                chunk_id = meta.get('chunk_id', f'chunk_{i}')

                quads = [
                    pymupdf.Rect(r[0], r[1], r[2], r[3]).quad
                    for r in rects
                    if len(r) == RECT_COORDS_COUNT
                ]
                if quads:
                    annot = page.add_highlight_annot(quads=quads)
                    annot.set_colors(stroke=color)
                    annot.set_opacity(0.4)
                    annot.set_info(
                        title=chunk_id,
                        content=f'{chunk_id} | {meta.get("section_path", "")}',
                    )
                    annot.update()

                    first = rects[0]
                    page.insert_text(
                        (first[0], max(first[1] - 1, 5)),
                        chunk_id.replace('chunk_', 'c'),
                        fontsize=4,
                        color=(0.3, 0.3, 0.3),
                    )

        pdf.save(str(output_pdf_path), garbage=3, deflate=True)


def export_ingestion_audit(  # noqa: PLR0913, PLR0917
    full_path: str,
    source_name: str,
    full_markdown: str,
    page_map: List[Dict[str, Any]],
    sections: List[Section],
    chunks: List[Document],
    audit_base_dir: Optional[Path] = None,
) -> None:
    """
    Grava os 4 subdiretórios de auditoria caso DEBUG_INGESTION_AUDIT
    esteja ativo.
    """
    base_dir = Path(audit_base_dir or SETTINGS.INGESTION_AUDIT_DIRECTORY)
    stem = Path(full_path).stem
    source_file = Path(full_path).name

    stage_1_dir = base_dir / '01_raw_markdown'
    stage_2_dir = base_dir / '02_sections_tree'
    stage_3_dir = base_dir / '03_chunks'
    stage_4_dir = base_dir / '04_annotated_pdfs'

    for d in (stage_1_dir, stage_2_dir, stage_3_dir, stage_4_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Estágio 1: Raw Markdown & Pages Map
    (stage_1_dir / f'{stem}.md').write_text(full_markdown, encoding='utf-8')
    pages_payload = {'source_file': source_file, 'pages': page_map}
    (stage_1_dir / f'{stem}_pages.json').write_text(
        json.dumps(pages_payload, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    # Estágio 2: Sections Tree
    all_flat = flatten_sections(sections)
    sec_payload = {
        'source_file': source_file,
        'total_sections': len(all_flat),
        'sections': tree_to_dict(sections),
    }
    (stage_2_dir / f'{stem}_sections.json').write_text(
        json.dumps(sec_payload, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    (stage_2_dir / f'{stem}_sections.md').write_text(
        tree_to_markdown(source_file, sections),
        encoding='utf-8',
    )

    # Estágio 3: Chunks
    chunk_payload = {
        'source_file': source_file,
        'total_chunks': len(chunks),
        'chunks': documents_to_dict(chunks),
    }
    (stage_3_dir / f'{stem}_chunks.json').write_text(
        json.dumps(chunk_payload, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    (stage_3_dir / f'{stem}_chunks.md').write_text(
        documents_to_markdown_preview(source_file, chunks),
        encoding='utf-8',
    )

    # Estágio 4: Annotated PDF
    annotated_pdf_path = stage_4_dir / f'{stem}_annotated.pdf'
    annotate_pdf_document(
        full_path=full_path,
        output_pdf_path=annotated_pdf_path,
        full_markdown=full_markdown,
        page_map=page_map,
        sections=sections,
        chunks=chunks,
    )
    logger.info(
        'Auditoria de ingestao concluida para %s em %s', stem, base_dir
    )
