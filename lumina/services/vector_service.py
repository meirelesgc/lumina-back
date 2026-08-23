import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

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


def _clean_and_format_documents(documents: List[Document]) -> List[Document]:
    chunks = SPLITTER.split_documents(documents)

    for i, chunk in enumerate(chunks):
        text = chunk.page_content or ''
        text = text.replace('\x00', '')
        text = re.sub(r'\s+', ' ', text).strip()
        section = (chunk.metadata.get('section_title') or '').strip()
        if section:
            chunk.page_content = f'SECTION: {section}\n\n{text}'
        else:
            chunk.page_content = text
        chunk.metadata['chunk_index'] = i
        chunk.metadata.setdefault('source', 'unknown')

        # Fallback fields for non-PDFs
        chunk.metadata['chunk_id'] = f'chunk_fallback_{i}'
        chunk.metadata['page'] = 0
        chunk.metadata['rects'] = []

    return chunks


class SectionInfo(BaseModel):
    section_name: str = Field(description='Nome normalizado da seção.')
    start_text: Optional[str] = Field(
        description='Trecho exato inicial da seção contendo entre 15 e 30 palavras.'
    )
    end_text: Optional[str] = Field(
        description='Trecho exato final da seção contendo entre 15 e 30 palavras.'
    )


class ChunkSections(BaseModel):
    sections: List[SectionInfo]


def _get_sections_with_model(
    documents: List[Document], model: BaseChatModel
) -> List[Dict[str, Any]]:
    full_text = '\n'.join(
        doc.page_content for doc in documents if doc.page_content
    )
    chunk_size = 3000
    chunks = [
        full_text[i : i + chunk_size]
        for i in range(0, len(full_text), chunk_size)
    ]

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
                contexto_prompt += f"- ATENÇÃO: O trecho atual inicia dentro da seção '{secao_aberta}', que não foi fechada no trecho anterior. NÃO crie um novo registro para esta seção. Retorne apenas as NOVAS seções que começarem neste texto.\n"
            else:
                contexto_prompt += '- Todas as seções anteriores foram encerradas. Procure pelo início da próxima seção.\n'

        prompt = f"""
        Identifique as seções no texto fornecido.
        
        {contexto_prompt}
        Instruções:
        - Extraia apenas as seções maiores. Ignore subseções.
        - Normalize o nome da seção.
        - Extraia o texto exato que inicia a seção. O trecho deve conter entre 15 e 30 palavras literais para garantir unicidade de busca. Marque como nulo caso o início esteja em um trecho anterior.
        - Extraia o texto exato que termina a seção. O trecho deve conter as últimas 15 a 30 palavras literais antes da próxima seção. Marque como nulo caso não encontre o fim neste trecho.

        Texto:
        {chunk}
        """

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
                        f"    -> [AJUSTE] Atualizado fim da seção aberta anterior '{sec.section_name}'."
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

    return all_sections


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


def _split_by_sections(
    documents: List[Document], model: BaseChatModel
) -> List[Document]:
    sections = _get_sections_with_model(documents, model)

    full_text = '\n'.join(doc.page_content for doc in documents)
    base_metadata = documents[0].metadata.copy()
    normalized_text, mapping = _normalize_with_mapping(full_text)

    valid_sections = []
    cursor = 0

    for section in sections:
        if not section['start_text']:
            continue
        start_normalized, _ = _normalize_with_mapping(section['start_text'])
        start_idx = normalized_text.find(start_normalized, cursor)

        if start_idx == -1:
            start_idx = normalized_text.find(start_normalized, 0)

        if start_idx != -1:
            valid_sections.append({
                'section': section['section'],
                'start_idx': start_idx,
                'end_text': section['end_text'],
            })
            cursor = start_idx

    split_documents = []

    for i in range(len(valid_sections)):
        current = valid_sections[i]
        start_idx = current['start_idx']
        end_idx = -1

        if current['end_text']:
            end_normalized, _ = _normalize_with_mapping(current['end_text'])
            end_idx = normalized_text.find(end_normalized, start_idx)

        if end_idx == -1 and i + 1 < len(valid_sections):
            end_idx = valid_sections[i + 1]['start_idx']

        if end_idx == -1:
            end_original = len(full_text)
        else:
            end_original = mapping[end_idx]

        start_original = mapping[start_idx]

        split_documents.append(
            Document(
                page_content=full_text[start_original:end_original],
                metadata={
                    **base_metadata,
                    'section_title': current['section'],
                },
            )
        )

    if not split_documents and documents:
        return documents

    return split_documents


def _assign_sections_to_chunks(
    chunks: List[Document], model: BaseChatModel
) -> List[Document]:
    sections = _get_sections_with_model(chunks, model)
    full_text = '\n'.join(doc.page_content for doc in chunks)
    normalized_text, mapping = _normalize_with_mapping(full_text)

    valid_sections = []
    cursor = 0
    for section in sections:
        if not section['start_text']:
            continue
        start_normalized, _ = _normalize_with_mapping(section['start_text'])
        start_idx = normalized_text.find(start_normalized, cursor)
        if start_idx == -1:
            start_idx = normalized_text.find(start_normalized, 0)
        if start_idx != -1:
            valid_sections.append({
                'section': section['section'],
                'start_idx': start_idx,
                'end_text': section['end_text'],
            })
            cursor = start_idx

    current_offset = 0
    for chunk in chunks:
        chunk_norm, _ = _normalize_with_mapping(chunk.page_content)
        chunk_start_idx = normalized_text.find(chunk_norm, current_offset)
        if chunk_start_idx == -1:
            chunk_start_idx = current_offset

        assigned_section = ''
        for sec in valid_sections:
            if sec['start_idx'] <= chunk_start_idx + len(chunk_norm) // 2:
                assigned_section = sec['section']
            else:
                break

        chunk.metadata['section_title'] = assigned_section

        if assigned_section:
            chunk.page_content = (
                f'SECTION: {assigned_section}\n\n{chunk.page_content}'
            )

        current_offset = chunk_start_idx + len(chunk_norm)

    return chunks


async def _anonymize_and_vectorize(chunks: List[Document], vstore: VStore):
    if not chunks:
        return
    anonymizer = PresidioAnonymizer()
    anonymized_chunks = anonymizer.anonymize_chunks(chunks)
    await vstore.aadd_documents(anonymized_chunks)


async def process_file(full_path: str, vstore: VStore, model) -> None:
    ext = os.path.splitext(full_path)[1].lower()
    source_name = f'lumina/storage/uploads/{os.path.basename(full_path)}'

    if ext == '.pdf':
        doc = fitz.open(full_path)
        chunker = CoordinateChunker(max_chars=500)
        raw_chunks = []
        global_chunk_idx = 0
        for i in range(len(doc)):
            page_chunks = chunker.process_page(doc, i)
            for pc in page_chunks:
                text = pc['text'].replace('\x00', '')
                text = re.sub(r'\s+', ' ', text).strip()
                if not text:
                    continue
                raw_chunks.append(
                    Document(
                        page_content=text,
                        metadata={
                            'chunk_id': pc['chunk_id'],
                            'chunk_index': global_chunk_idx,
                            'page': pc['page'],
                            'rects': pc['rects'],
                            'source': source_name,
                        },
                    )
                )
                global_chunk_idx += 1

        formatted_documents = _assign_sections_to_chunks(raw_chunks, model)
    elif ext == '.docx':
        loader = Docx2txtLoader(full_path)
        raw_documents = loader.load()
        section_documents = _split_by_sections(raw_documents, model)
        formatted_documents = _clean_and_format_documents(section_documents)
        for doc in formatted_documents:
            doc.metadata['source'] = source_name
    elif ext == '.txt':
        loader = TextLoader(full_path, encoding='utf-8')
        raw_documents = loader.load()
        section_documents = _split_by_sections(raw_documents, model)
        formatted_documents = _clean_and_format_documents(section_documents)
        for doc in formatted_documents:
            doc.metadata['source'] = source_name
    else:
        raise ValueError(f'Tipo de arquivo não suportado: {ext}')

    await _anonymize_and_vectorize(formatted_documents, vstore)


async def create_vectors(
    file_path: Path, vstore: VStore, model: Model
) -> None:
    unique_filename = str(file_path).split('/')[-1]
    full_path = os.path.join(SETTINGS.UPLOAD_DIRECTORY, unique_filename)
    if not os.path.exists(full_path):
        return
    await process_file(full_path, vstore, model)
