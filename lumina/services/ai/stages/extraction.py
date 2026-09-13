import re
from datetime import datetime
from typing import Any, List, Optional, Tuple
from uuid import UUID

import fitz
from langchain_community.document_loaders import (
    Docx2txtLoader,
    TextLoader,
)
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from lumina.services.run_logger import get_run_logger

SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)


class CoordinateChunker:
    """
    Agrupa palavras extraídas pelo PyMuPDF em linhas lógicas e fatias
    de texto com teto de caracteres (max_chars), preservando as caixas
    delimitadoras (rects) de cada linha.
    """

    def __init__(self, max_chars: int = 500):
        self.max_chars = max_chars

    def process_page(self, doc: Any, page_num: int) -> List[dict]:
        page = doc[page_num]
        words = page.get_text('words')
        chunks = []
        current_chunk_text = ''
        current_chunk_rects = []
        current_line_key = None
        line_words = []

        def process_line(l_words: list):
            nonlocal current_chunk_text, current_chunk_rects
            if not l_words:
                return
            lx0 = min(w[0] for w in l_words)
            ly0 = min(w[1] for w in l_words)
            lx1 = max(w[2] for w in l_words)
            ly1 = max(w[3] for w in l_words)
            line_text = ' '.join(w[4] for w in l_words)

            if (
                len(current_chunk_text) + len(line_text) + 1 > self.max_chars
                and current_chunk_text
            ):
                chunks.append({
                    'chunk_id': f'chunk_{page_num}_{len(chunks)}',
                    'page': page_num,
                    'text': current_chunk_text.strip(),
                    'rects': current_chunk_rects.copy(),
                })
                current_chunk_text = line_text + ' '
                current_chunk_rects = [[lx0, ly0, lx1, ly1]]
            else:
                current_chunk_text += line_text + ' '
                current_chunk_rects.append([lx0, ly0, lx1, ly1])

        for w in words:
            block_no = w[5]
            line_no = w[6]
            key = (block_no, line_no)
            if current_line_key != key:
                if current_line_key is not None:
                    process_line(line_words)
                current_line_key = key
                line_words = []
            line_words.append(w)

        if line_words:
            process_line(line_words)

        if current_chunk_text:
            chunks.append({
                'chunk_id': f'chunk_{page_num}_{len(chunks)}',
                'page': page_num,
                'text': current_chunk_text.strip(),
                'rects': current_chunk_rects.copy(),
            })

        return chunks


def clean_and_format_documents(
    documents: List[Document],
) -> Tuple[List[Document], int, int]:
    """
    Fatia documentos em blocos de até 500 caracteres, removendo bytes nulos
    e normalizando espaços. Retorna os chunks e contadores de sanitização.
    """
    chunks = SPLITTER.split_documents(documents)
    null_bytes_count = 0
    whitespace_count = 0

    for i, chunk in enumerate(chunks):
        raw_text = chunk.page_content or ''
        if '\x00' in raw_text:
            null_bytes_count += raw_text.count('\x00')
            raw_text = raw_text.replace('\x00', '')
        cleaned_text = re.sub(r'\s+', ' ', raw_text).strip()
        if cleaned_text != raw_text:
            whitespace_count += 1

        section = (chunk.metadata.get('section_title') or '').strip()
        if section:
            chunk.page_content = f'SECTION: {section}\n\n{cleaned_text}'
        else:
            chunk.page_content = cleaned_text
        chunk.metadata['chunk_index'] = i
        chunk.metadata.setdefault('source', 'unknown')

        # Fallback para arquivos sem layout fixo
        chunk.metadata['chunk_id'] = f'chunk_fallback_{i}'
        chunk.metadata['page'] = 0
        chunk.metadata['rects'] = []

    return chunks, null_bytes_count, whitespace_count


def extract_pdf_chunks(
    full_path: str, source_name: str
) -> Tuple[List[Document], int, int, int]:
    """
    Extrai blocos de texto geométricos de PDF utilizando PyMuPDF.
    Retorna (chunks, pages_count, null_bytes, whitespace_ops).
    """
    doc = fitz.open(full_path)
    pages_count = len(doc)
    chunker = CoordinateChunker(max_chars=500)
    raw_chunks = []
    null_bytes = 0
    ws_ops = 0

    for i in range(pages_count):
        for pc in chunker.process_page(doc, i):
            text = pc['text']
            if '\x00' in text:
                null_bytes += text.count('\x00')
                text = text.replace('\x00', '')
            cleaned = re.sub(r'\s+', ' ', text).strip()
            if cleaned != text:
                ws_ops += 1
            if not cleaned:
                continue
            raw_chunks.append(
                Document(
                    page_content=cleaned,
                    metadata={
                        'chunk_id': pc['chunk_id'],
                        'chunk_index': len(raw_chunks),
                        'page': pc['page'],
                        'rects': pc['rects'],
                        'source': source_name,
                    },
                )
            )
    return raw_chunks, pages_count, null_bytes, ws_ops


def load_raw_text_docs(full_path: str, ext: str) -> Tuple[List[Document], str]:
    """
    Carrega documentos brutos DOCX ou TXT.
    """
    if ext == '.docx':
        return Docx2txtLoader(full_path).load(), 'Docx2txtLoader'
    return TextLoader(full_path, encoding='utf-8').load(), 'TextLoader'


async def extract_pdf_with_telemetry(
    full_path: str,
    source_name: str,
    run_id: Optional[UUID] = None,
) -> Tuple[List[Document], int]:
    """
    Executa a extração do PDF com rastreamento no RunLogger.
    """
    run_logger = get_run_logger()
    t_start = datetime.now()
    if run_id:
        await run_logger.start_stage(run_id=run_id, stage='extraction')

    try:
        raw_chunks, pages_count, null_bytes, ws_ops = extract_pdf_chunks(
            full_path, source_name
        )
        chunks_count = len(raw_chunks)
        avg_sz = (
            round(
                sum(len(c.page_content) for c in raw_chunks) / chunks_count,
                1,
            )
            if chunks_count
            else 0.0
        )
        if run_id:
            d_ms = int((datetime.now() - t_start).total_seconds() * 1000)
            await run_logger.complete_stage(
                run_id=run_id,
                stage='extraction',
                duration_ms=d_ms,
                item_count=chunks_count,
                data={
                    'pages_count': pages_count,
                    'chunks_count': chunks_count,
                    'avg_chunk_size': avg_sz,
                    'extractor_type': 'PyMuPDF',
                    'sanitization_ops_count': {
                        'null_bytes_removed': null_bytes,
                        'whitespace_normalized': ws_ops,
                    },
                },
            )
        return raw_chunks, pages_count
    except Exception as e:
        if run_id:
            d_ms = int((datetime.now() - t_start).total_seconds() * 1000)
            await run_logger.fail_stage(
                run_id=run_id,
                stage='extraction',
                error=str(e),
                duration_ms=d_ms,
            )
        raise


async def format_text_docs_with_telemetry(
    section_docs: List[Document],
    source_name: str,
    pages_count: int,
    extractor_type: str,
    run_id: Optional[UUID] = None,
) -> List[Document]:
    """
    Formata documentos DOCX/TXT em blocos com rastreamento no RunLogger.
    """
    run_logger = get_run_logger()
    t_ext = datetime.now()
    if run_id:
        await run_logger.start_stage(run_id=run_id, stage='extraction')
    try:
        formatted_docs, null_cnt, ws_cnt = clean_and_format_documents(
            section_docs
        )
        for doc in formatted_docs:
            doc.metadata['source'] = source_name
        chunks_count = len(formatted_docs)
        avg_sz = (
            round(
                sum(len(c.page_content) for c in formatted_docs)
                / chunks_count,
                1,
            )
            if chunks_count
            else 0.0
        )
        if run_id:
            d_ext = int((datetime.now() - t_ext).total_seconds() * 1000)
            await run_logger.complete_stage(
                run_id=run_id,
                stage='extraction',
                duration_ms=d_ext,
                item_count=chunks_count,
                data={
                    'pages_count': pages_count,
                    'chunks_count': chunks_count,
                    'avg_chunk_size': avg_sz,
                    'extractor_type': extractor_type,
                    'sanitization_ops_count': {
                        'null_bytes_removed': null_cnt,
                        'whitespace_normalized': ws_cnt,
                    },
                },
            )
        return formatted_docs
    except Exception as e:
        if run_id:
            d_ext = int((datetime.now() - t_ext).total_seconds() * 1000)
            await run_logger.fail_stage(
                run_id=run_id,
                stage='extraction',
                error=str(e),
                duration_ms=d_ext,
            )
        raise
