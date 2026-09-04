import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import fitz
from langchain_community.document_loaders import (
    Docx2txtLoader,
    TextLoader,
)
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

from lumina.core.dependencies import Model, VStore
from lumina.core.settings import Settings
from lumina.services.run_logger import get_run_logger
from lumina.utils.PresidioAnonymizer import PresidioAnonymizer

SETTINGS = Settings()

SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)


class CoordinateChunker:
    def __init__(self, max_chars=500):
        self.max_chars = max_chars

    def process_page(self, doc, page_num):
        page = doc[page_num]
        words = page.get_text('words')
        chunks = []
        current_chunk_text = ''
        current_chunk_rects = []
        current_line_key = None
        line_words = []

        def process_line(l_words):
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


def _clean_and_format_documents(
    documents: List[Document],
) -> Tuple[List[Document], int, int]:
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

        # Fallback fields for non-PDFs
        chunk.metadata['chunk_id'] = f'chunk_fallback_{i}'
        chunk.metadata['page'] = 0
        chunk.metadata['rects'] = []

    return chunks, null_bytes_count, whitespace_count


class SectionInfo(BaseModel):
    section_name: str = Field(description='Nome normalizado da seção.')
    start_text: Optional[str] = Field(
        description=(
            'Trecho exato inicial da seção contendo entre 15 e 30 palavras.'
        )
    )
    end_text: Optional[str] = Field(
        description=(
            'Trecho exato final da seção contendo entre 15 e 30 palavras.'
        )
    )


class ChunkSections(BaseModel):
    sections: List[SectionInfo]


def _get_sections_with_model(
    documents: List[Document], model: BaseChatModel
) -> Tuple[List[Dict[str, Any]], str]:
    full_text = '\n'.join(
        doc.page_content for doc in documents if doc.page_content
    )
    chunk_size = 3000
    chunks = [
        full_text[i : i + chunk_size]
        for i in range(0, len(full_text), chunk_size)
    ]
    first_window = chunks[0] if chunks else ''

    structured_model = model.with_structured_output(ChunkSections)
    all_sections = []

    for idx, chunk in enumerate(chunks):
        print(f'PROCESSANDO CHUNK [{idx}/{len(chunks)}]')
        contexto_prompt = ''
        if all_sections:
            nomes_secoes = [s['section'] for s in all_sections]
            contexto_prompt += 'Contexto Histórico:\n'
            contexto_prompt += (
                f'- Seções já identificadas: {", ".join(nomes_secoes)}\n'
            )

            if all_sections[-1]['end_text'] is None:
                secao_aberta = all_sections[-1]['section']
                contexto_prompt += (
                    f'- ATENÇÃO: O trecho atual inicia dentro da seção '
                    f"'{secao_aberta}', que não foi fechada no trecho "
                    f'anterior. NÃO crie um novo registro para esta seção. '
                    f'Retorne apenas as NOVAS seções que começarem neste '
                    f'texto.\n'
                )
            else:
                contexto_prompt += (
                    '- Todas as seções anteriores foram encerradas. '
                    'Procure pelo início da próxima seção.\n'
                )

        prompt = (
            'Identifique as seções no texto fornecido.\n\n'
            f'{contexto_prompt}\n'
            'Instruções:\n'
            '- Extraia apenas as seções maiores. Ignore subseções.\n'
            '- Normalize o nome da seção.\n'
            '- Extraia o texto exato que inicia a seção. O trecho deve '
            'conter entre 15 e 30 palavras literais para garantir '
            'unicidade de busca. Marque como nulo caso o início esteja em '
            'um trecho anterior.\n'
            '- Extraia o texto exato que termina a seção. O trecho deve '
            'conter as últimas 15 a 30 palavras literais antes da '
            'próxima seção. Marque como nulo caso não encontre o fim neste '
            'trecho.\n\n'
            f'Texto:\n{chunk}\n'
        )

        try:
            response = structured_model.invoke(prompt)
        except Exception as e:
            print(f'Erro na extração de seções: {e}')
            continue

        if not response or not response.sections:
            continue

        for sec in response.sections:
            if (
                all_sections
                and all_sections[-1]['end_text'] is None
                and sec.section_name.lower()
                == all_sections[-1]['section'].lower()
            ):
                if sec.end_text:
                    all_sections[-1]['end_text'] = sec.end_text
                    print(
                        f'    -> [AJUSTE] Atualizado fim da seção aberta '
                        f"anterior '{sec.section_name}'."
                    )
                continue

            all_sections.append({
                'section': sec.section_name,
                'start_text': sec.start_text,
                'end_text': sec.end_text,
            })

    for i in range(len(all_sections)):
        if all_sections[i]['end_text'] is None and i + 1 < len(all_sections):
            proximo_inicio = all_sections[i + 1]['start_text']
            all_sections[i]['end_text'] = proximo_inicio

    return all_sections, first_window


def _normalize_with_mapping(text: str):
    normalized = []
    mapping = []
    previous_space = False

    if not text:
        return ''.join(normalized), mapping

    for original_idx, char in enumerate(text):
        nfkd = unicodedata.normalize('NFKD', char)
        chars = [c for c in nfkd if unicodedata.category(c) != 'Mn']

        if not chars:
            continue

        char_norm = chars[0]

        if char_norm.isspace():
            if not previous_space:
                normalized.append(' ')
                mapping.append(original_idx)
                previous_space = True
            continue

        previous_space = False

        if char_norm.isprintable():
            normalized.append(char_norm.lower())
            mapping.append(original_idx)

    return ''.join(normalized), mapping


def _find_valid_sections(
    sections: List[Dict[str, Any]], normalized_text: str
) -> List[Dict[str, Any]]:
    valid_sections = []
    cursor = 0
    for section in sections:
        if not section.get('start_text'):
            continue
        start_norm, _ = _normalize_with_mapping(section['start_text'])
        start_idx = normalized_text.find(start_norm, cursor)
        if start_idx == -1:
            start_idx = normalized_text.find(start_norm, 0)
        if start_idx != -1:
            valid_sections.append({
                'section': section['section'],
                'start_idx': start_idx,
                'end_text': section.get('end_text'),
            })
            cursor = start_idx
    return valid_sections


def _build_sections_meta(
    sections: List[Dict[str, Any]],
    valid_sections: List[Dict[str, Any]],
    first_window: str,
) -> Dict[str, Any]:
    rate = round(len(valid_sections) / len(sections), 2) if sections else 1.0
    return {
        'input_window_text': (
            first_window if SETTINGS.DEBUG_PIPELINE_RUNS else ''
        ),
        'sections_detected': [
            {
                'section_name': s['section'],
                'start_text': s.get('start_text'),
                'end_text': s.get('end_text'),
            }
            for s in sections
        ],
        'mapping_success_rate': rate,
    }


def _slice_sections_from_text(
    valid_sections: List[Dict[str, Any]],
    full_text: str,
    normalized_text: str,
    mapping: List[int],
    base_metadata: Dict[str, Any],
) -> List[Document]:
    split_documents = []
    for i, current in enumerate(valid_sections):
        start_idx = current['start_idx']
        end_idx = -1
        if current.get('end_text'):
            end_norm, _ = _normalize_with_mapping(current['end_text'])
            end_idx = normalized_text.find(end_norm, start_idx)

        if end_idx == -1 and i + 1 < len(valid_sections):
            end_idx = valid_sections[i + 1]['start_idx']

        end_orig = mapping[end_idx] if end_idx != -1 else len(full_text)
        start_orig = mapping[start_idx]

        split_documents.append(
            Document(
                page_content=full_text[start_orig:end_orig],
                metadata={
                    **base_metadata,
                    'section_title': current['section'],
                },
            )
        )
    return split_documents


def _split_by_sections(
    documents: List[Document], model: BaseChatModel
) -> Tuple[List[Document], Dict[str, Any]]:
    sections, first_window = _get_sections_with_model(documents, model)
    full_text = '\n'.join(doc.page_content for doc in documents)
    base_metadata = documents[0].metadata.copy() if documents else {}
    normalized_text, mapping = _normalize_with_mapping(full_text)

    valid_sections = _find_valid_sections(sections, normalized_text)
    sections_meta = _build_sections_meta(
        sections, valid_sections, first_window
    )
    split_docs = _slice_sections_from_text(
        valid_sections, full_text, normalized_text, mapping, base_metadata
    )
    return split_docs or documents, sections_meta


def _apply_sections_to_chunks(
    chunks: List[Document],
    valid_sections: List[Dict[str, Any]],
    normalized_text: str,
) -> List[Document]:
    current_offset = 0
    for chunk in chunks:
        chunk_norm, _ = _normalize_with_mapping(chunk.page_content)
        start_idx = normalized_text.find(chunk_norm, current_offset)
        if start_idx == -1:
            start_idx = current_offset

        assigned = ''
        for sec in valid_sections:
            if sec['start_idx'] <= start_idx + len(chunk_norm) // 2:
                assigned = sec['section']
            else:
                break

        chunk.metadata['section_title'] = assigned
        if assigned:
            chunk.page_content = f'SECTION: {assigned}\n\n{chunk.page_content}'
        current_offset = start_idx + len(chunk_norm)
    return chunks


def _assign_sections_to_chunks(
    chunks: List[Document], model: BaseChatModel
) -> Tuple[List[Document], Dict[str, Any]]:
    sections, first_window = _get_sections_with_model(chunks, model)
    full_text = '\n'.join(doc.page_content for doc in chunks)
    normalized_text, _ = _normalize_with_mapping(full_text)

    valid_sections = _find_valid_sections(sections, normalized_text)
    sections_meta = _build_sections_meta(
        sections, valid_sections, first_window
    )
    assigned_chunks = _apply_sections_to_chunks(
        chunks, valid_sections, normalized_text
    )
    return assigned_chunks, sections_meta


def _extract_entities_count(replacement_keys: List[str]) -> Dict[str, int]:
    entities_count: Dict[str, int] = {}
    for k in replacement_keys:
        match = re.match(r'<([A-Za-z0-9_]+)_\d+>', k)
        if not match:
            continue
        ent = match.group(1)
        if 'PHONE' in ent:
            ent_key = 'PHONE'
        elif 'EMAIL' in ent:
            ent_key = 'EMAIL'
        else:
            ent_key = ent
        entities_count[ent_key] = entities_count.get(ent_key, 0) + 1
    return entities_count


async def _anonymize_chunks(
    chunks: List[Document], run_id: Optional[UUID] = None
) -> List[Document]:
    run_logger = get_run_logger()
    t_start = datetime.now()
    if run_id:
        await run_logger.start_stage(run_id=run_id, stage='anonymization')

    try:
        anonymizer = PresidioAnonymizer()
        anonymized = anonymizer.anonymize_chunks(chunks)
        keys = list(anonymizer.existing_presidio_mapping.keys())
        counts = _extract_entities_count(keys)
        if run_id:
            d_ms = int((datetime.now() - t_start).total_seconds() * 1000)
            await run_logger.complete_stage(
                run_id=run_id,
                stage='anonymization',
                duration_ms=d_ms,
                item_count=len(keys),
                data={
                    'entities_detected_count': counts,
                    'replacement_keys': keys,
                },
            )
        return anonymized
    except Exception as e:
        if run_id:
            d_ms = int((datetime.now() - t_start).total_seconds() * 1000)
            await run_logger.fail_stage(
                run_id=run_id,
                stage='anonymization',
                error=str(e),
                duration_ms=d_ms,
            )
        raise


async def _vectorize_chunks(
    chunks: List[Document],
    vstore: VStore,
    run_id: Optional[UUID] = None,
) -> None:
    run_logger = get_run_logger()
    t_start = datetime.now()
    if run_id:
        await run_logger.start_stage(run_id=run_id, stage='embeddings')

    try:
        await vstore.aadd_documents(chunks)
        if run_id:
            d_ms = int((datetime.now() - t_start).total_seconds() * 1000)
            await run_logger.complete_stage(
                run_id=run_id,
                stage='embeddings',
                duration_ms=d_ms,
                item_count=len(chunks),
                data={'chunks_count': len(chunks)},
            )
    except Exception as e:
        if run_id:
            d_embed = int((datetime.now() - t_start).total_seconds() * 1000)
            await run_logger.fail_stage(
                run_id=run_id,
                stage='embeddings',
                error=str(e),
                duration_ms=d_embed,
            )
        raise


async def _anonymize_and_vectorize(
    chunks: List[Document],
    vstore: VStore,
    run_id: Optional[UUID] = None,
) -> None:
    if not chunks:
        return
    anonymized = await _anonymize_chunks(chunks, run_id=run_id)
    await _vectorize_chunks(anonymized, vstore, run_id=run_id)


def _extract_pdf_chunks(
    full_path: str, source_name: str
) -> Tuple[List[Document], int, int, int]:
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


async def _process_pdf_file(
    full_path: str,
    source_name: str,
    model: Any,
    run_id: Optional[UUID] = None,
) -> List[Document]:
    run_logger = get_run_logger()
    t_start = datetime.now()
    if run_id:
        await run_logger.start_stage(run_id=run_id, stage='extraction')

    try:
        raw_chunks, pages_count, null_bytes, ws_ops = _extract_pdf_chunks(
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

    t_sec = datetime.now()
    if run_id:
        await run_logger.start_stage(run_id=run_id, stage='sections')
    try:
        formatted_docs, sections_meta = _assign_sections_to_chunks(
            raw_chunks, model
        )
        if run_id:
            d_sec = int((datetime.now() - t_sec).total_seconds() * 1000)
            await run_logger.complete_stage(
                run_id=run_id,
                stage='sections',
                duration_ms=d_sec,
                item_count=len(sections_meta.get('sections_detected', [])),
                data=sections_meta,
            )
        return formatted_docs
    except Exception as e:
        if run_id:
            d_sec = int((datetime.now() - t_sec).total_seconds() * 1000)
            await run_logger.fail_stage(
                run_id=run_id,
                stage='sections',
                error=str(e),
                duration_ms=d_sec,
            )
        raise


def _load_raw_text_docs(
    full_path: str, ext: str
) -> Tuple[List[Document], str]:
    if ext == '.docx':
        return Docx2txtLoader(full_path).load(), 'Docx2txtLoader'
    return TextLoader(full_path, encoding='utf-8').load(), 'TextLoader'


async def _process_text_docx_file(
    full_path: str,
    ext: str,
    source_name: str,
    model: Any,
    run_id: Optional[UUID] = None,
) -> List[Document]:
    run_logger = get_run_logger()
    raw_docs, extractor_type = _load_raw_text_docs(full_path, ext)
    pages_count = len(raw_docs)

    t_sec = datetime.now()
    if run_id:
        await run_logger.start_stage(run_id=run_id, stage='sections')
    try:
        section_docs, sections_meta = _split_by_sections(raw_docs, model)
        if run_id:
            d_sec = int((datetime.now() - t_sec).total_seconds() * 1000)
            await run_logger.complete_stage(
                run_id=run_id,
                stage='sections',
                duration_ms=d_sec,
                item_count=len(sections_meta.get('sections_detected', [])),
                data=sections_meta,
            )
    except Exception as e:
        if run_id:
            d_sec = int((datetime.now() - t_sec).total_seconds() * 1000)
            await run_logger.fail_stage(
                run_id=run_id,
                stage='sections',
                error=str(e),
                duration_ms=d_sec,
            )
        raise

    t_ext = datetime.now()
    if run_id:
        await run_logger.start_stage(run_id=run_id, stage='extraction')
    try:
        formatted_docs, null_cnt, ws_cnt = _clean_and_format_documents(
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


async def process_file(
    full_path: str,
    vstore: VStore,
    model: Any,
    run_id: Optional[UUID] = None,
) -> None:
    ext = os.path.splitext(full_path)[1].lower()
    source_name = f'lumina/storage/uploads/{os.path.basename(full_path)}'

    if ext == '.pdf':
        formatted_docs = await _process_pdf_file(
            full_path, source_name, model, run_id=run_id
        )
    elif ext in {'.docx', '.txt'}:
        formatted_docs = await _process_text_docx_file(
            full_path, ext, source_name, model, run_id=run_id
        )
    else:
        raise ValueError(f'Tipo de arquivo não suportado: {ext}')

    await _anonymize_and_vectorize(formatted_docs, vstore, run_id=run_id)


async def create_vectors(
    file_path: Path,
    vstore: VStore,
    model: Model,
    run_id: Optional[UUID] = None,
) -> None:
    unique_filename = str(file_path).split('/')[-1]
    full_path = os.path.join(SETTINGS.UPLOAD_DIRECTORY, unique_filename)
    if not os.path.exists(full_path):
        return
    await process_file(full_path, vstore, model, run_id=run_id)
