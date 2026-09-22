import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from lumina.core.settings import Settings
from lumina.services.ai.stages.contextualization import (
    DocumentMetadata,
    generate_chunk_context,
)
from lumina.services.ai.stages.section_models import Section

SETTINGS = Settings()

ChunkCleaner = Callable[[List[Document]], List[Document]]


def clean_whitespace(docs: List[Document]) -> List[Document]:
    """
    Normaliza espacos em branco e saltos de linha multiplos continuos.
    """
    for doc in docs:
        doc.page_content = re.sub(r'\n{3,}', '\n\n', doc.page_content).strip()
    return docs


def get_default_chunk_cleaners() -> List[ChunkCleaner]:
    return [clean_whitespace]


def run_chunk_pipeline(
    docs: List[Document],
    cleaners: Optional[Sequence[ChunkCleaner]] = None,
) -> List[Document]:
    if cleaners is None:
        cleaners = get_default_chunk_cleaners()

    current_docs = docs
    for cleaner in cleaners:
        current_docs = cleaner(current_docs)

    return current_docs


def create_default_text_splitter(
    chunk_size: int = 1000, chunk_overlap: int = 150
) -> RecursiveCharacterTextSplitter:
    """
    Cria o fatiador de texto do LangChain configurado para Markdown.
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=['\n\n', '\n', '. ', '; ', ', ', ' ', ''],
    )


def locate_pieces(content: str, texts: List[str]) -> List[Tuple[str, int]]:
    """
    Localiza o offset de cada fragmento do splitter dentro do conteudo.
    """
    pieces: List[Tuple[str, int]] = []
    cursor = 0
    for text in texts:
        idx = content.find(text, cursor)
        if idx < 0:
            idx = content.find(text)
        if idx < 0:
            idx = cursor
        pieces.append((text, idx))
        cursor = idx + 1
    return pieces


def slice_section_by_pages(
    section: Section,
    page_map: List[Dict[str, Any]],
    full_markdown: str,
) -> List[Dict[str, Any]]:
    """
    Corta o conteudo da secao estritamente nos limites de cada pagina.
    Retorna fatias com garantia de pertencer a exatamente 1 pagina (0-based).
    """
    if section.char_start is None or section.char_end is None:
        return []

    sec_start = section.char_start
    sec_end = section.char_end
    if sec_start >= sec_end:
        return []

    slices: List[Dict[str, Any]] = []

    for p in page_map:
        p_start = p['char_start']
        p_end = p_start + p.get('char_count', 0)

        # Intersecao [sec_start, sec_end) com [p_start, p_end)
        overlap_start = max(sec_start, p_start)
        overlap_end = min(sec_end, p_end)

        if overlap_start < overlap_end:
            raw_slice = full_markdown[overlap_start:overlap_end]
            clean_slice = raw_slice.strip()
            if not clean_slice:
                continue

            # Ajuste de offsets relativos ao strip()
            l_strip = len(raw_slice) - len(raw_slice.lstrip())
            r_strip = len(raw_slice) - len(raw_slice.rstrip())
            final_start = overlap_start + l_strip
            final_end = overlap_end - r_strip

            slices.append({
                'page': p['page'],
                'text': clean_slice,
                'char_start': final_start,
                'char_end': final_end,
                'section': section,
            })

    return slices


def create_chunks_from_sections(  # noqa: PLR0914
    sections: List[Section],
    page_map: List[Dict[str, Any]],
    full_markdown: str,
    source_name: str,
    splitter: Optional[RecursiveCharacterTextSplitter] = None,
) -> List[Document]:
    """
    Converte as secoes em Documents do LangChain fatiados por pagina.
    Garante page: int (0-based) e metadados aditivos ricos.
    """
    if splitter is None:
        splitter = create_default_text_splitter()

    docs_by_page: Dict[int, List[Document]] = {}
    all_docs: List[Document] = []

    for sec_idx, sec in enumerate(sections):
        page_slices = slice_section_by_pages(sec, page_map, full_markdown)
        section_title = sec.title
        breadcrumb_str = ' > '.join(sec.breadcrumb)
        confidence = (
            'numbered'
            if sec.heading.level_source == 'numbering_pattern'
            else 'font_derived'
        )
        role_str = (
            sec.role.value if hasattr(sec.role, 'value') else str(sec.role)
        )

        for slice_item in page_slices:
            slice_text = slice_item['text']
            slice_page = slice_item['page']
            slice_start = slice_item['char_start']

            if len(slice_text) <= splitter._chunk_size:
                pieces = [(slice_text, 0)]
            else:
                pieces = locate_pieces(
                    slice_text, splitter.split_text(slice_text)
                )

            for chunk_sub_idx, (text, offset_in_slice) in enumerate(pieces):
                clean_text = text.strip()
                if not clean_text:
                    continue

                chunk_cstart = slice_start + offset_in_slice
                chunk_cend = chunk_cstart + len(text)

                prefixed_content = f'[{section_title}] {clean_text}'

                metadata = {
                    'section_title': section_title,
                    'section_path': breadcrumb_str,
                    'section_level': sec.heading.level,
                    'level_source': sec.heading.level_source,
                    'hierarchy_confidence': confidence,
                    'section_role': role_str,
                    'role_confidence': sec.role_confidence,
                    'section_index': sec_idx,
                    'chunk_index_in_section': chunk_sub_idx,
                    'page': slice_page,
                    'source': source_name,
                    'char_start': chunk_cstart,
                    'char_end': chunk_cend,
                    'pipeline_version': 'v2',
                }

                doc = Document(
                    page_content=prefixed_content,
                    metadata=metadata,
                )

                if SETTINGS.CONTEXTUAL_CHUNK_ENRICHMENT_ENABLED:
                    chunk_context = generate_chunk_context(
                        doc, sec, DocumentMetadata(source_name=source_name)
                    )
                    if chunk_context:
                        doc.metadata['chunk_context'] = chunk_context

                docs_by_page.setdefault(slice_page, []).append(doc)
                all_docs.append(doc)

    # Atribuicao do chunk_id no formato legado: chunk_{page}_{idx_na_pagina}
    for page_num, p_docs in docs_by_page.items():
        for idx_in_page, doc in enumerate(p_docs):
            doc.metadata['chunk_id'] = f'chunk_{page_num}_{idx_in_page}'

    # Atribuicao sequencial global de chunk_index para ordenacao em retrieval
    for global_idx, doc in enumerate(all_docs):
        doc.metadata['chunk_index'] = global_idx

    return run_chunk_pipeline(all_docs)


def documents_to_dict(docs: List[Document]) -> List[Dict[str, Any]]:
    """
    Serializa lista de Documents para dicionários utilizáveis em JSON.
    """
    return [
        {
            'page_content': doc.page_content,
            'metadata': doc.metadata,
            'char_count': len(doc.page_content),
        }
        for doc in docs
    ]


def documents_to_markdown_preview(
    source_name: str, docs: List[Document]
) -> str:
    """
    Gera visualização de inspeção rápida em Markdown dos chunks gerados.
    """
    lines = [
        f'# Chunks Gerados: {source_name}',
        '',
        f'Total de chunks: **{len(docs)}**',
        '',
    ]

    for idx, doc in enumerate(docs, start=1):
        meta = doc.metadata
        page_val = meta.get('page', meta.get('page_number', '-'))
        level_val = meta.get('section_level', '-')
        lines.append(
            f'### Chunk {idx} (Pág: {page_val} | Nível: H{level_val})'
        )
        lines.append(f'**Caminho**: `{meta.get("section_path", "")}`  ')
        lines.append(f'**Tamanho**: {len(doc.page_content)} caracteres')
        lines.append('')
        lines.append('```text')
        lines.append(doc.page_content)
        lines.append('```')
        lines.append('')
        lines.append('---')
        lines.append('')

    return '\n'.join(lines) + '\n'
