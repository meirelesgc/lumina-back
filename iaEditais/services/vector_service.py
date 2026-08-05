import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyMuPDFLoader,
    TextLoader,
)
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

from iaEditais.core.dependencies import Model, VStore
from iaEditais.core.settings import Settings
from iaEditais.utils.PresidioAnonymizer import PresidioAnonymizer

SETTINGS = Settings()

SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)


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

        response = structured_model.invoke(prompt)

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

    with open('/tmp/sections.py', 'w', encoding='utf-8') as py:
        print('Salvando: [/tmp/sections.py]')
        py.write(str(sections))

    full_text = '\n'.join(doc.page_content for doc in documents)
    base_metadata = documents[0].metadata.copy()
    normalized_text, mapping = _normalize_with_mapping(full_text)

    valid_sections = []
    cursor = 0

    for section in sections:
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

    return split_documents


async def _anonymize_and_vectorize(chunks: List[Document], vstore: VStore):
    if not chunks:
        return
    anonymizer = PresidioAnonymizer()
    anonymized_chunks = anonymizer.anonymize_chunks(chunks)
    await vstore.aadd_documents(anonymized_chunks)


async def process_file(full_path: str, vstore: VStore, model) -> None:
    ext = os.path.splitext(full_path)[1].lower()

    if ext == '.pdf':
        loader = PyMuPDFLoader(full_path, mode='single')
    elif ext == '.docx':
        loader = Docx2txtLoader(full_path)
    elif ext == '.txt':
        loader = TextLoader(full_path, encoding='utf-8')
    else:
        raise ValueError(f'Tipo de arquivo não suportado: {ext}')

    raw_documents = loader.load()
    section_documents = _split_by_sections(raw_documents, model)
    formatted_documents = _clean_and_format_documents(section_documents)
    with open('/tmp/formatted_documents.py', 'w', encoding='utf-8') as py:
        # print('Salvando: [/tmp/formatted_documents.py]')
        # py.write(str(formatted_documents))
        pass
    await _anonymize_and_vectorize(formatted_documents, vstore)


async def create_vectors(
    file_path: Path, vstore: VStore, model: Model
) -> None:
    unique_filename = str(file_path).split('/')[-1]
    full_path = os.path.join(SETTINGS.UPLOAD_DIRECTORY, unique_filename)
    if not os.path.exists(full_path):
        return
    await process_file(full_path, vstore, model)
