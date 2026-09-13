import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from lumina.core.settings import Settings
from lumina.services.run_logger import get_run_logger

SETTINGS = Settings()


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


def detect_sections_with_model(
    documents: List[Document], model: BaseChatModel
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Identifica macro-seções utilizando a LLM em janelas de 3.000 caracteres.
    Retorna uma tupla: (lista_de_secoes, primeira_janela_de_texto).
    """
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


def normalize_with_mapping(text: str) -> Tuple[str, List[int]]:
    """
    Normaliza a string removendo diacríticos (NFKD) e construindo
    um vetor mapping[normalized_idx] -> original_idx.
    """
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


def find_valid_sections(
    sections: List[Dict[str, Any]], normalized_text: str
) -> List[Dict[str, Any]]:
    valid_sections = []
    cursor = 0
    for section in sections:
        if not section.get('start_text'):
            continue
        start_norm, _ = normalize_with_mapping(section['start_text'])
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


def build_sections_meta(
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


def slice_sections_from_text(
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
            end_norm, _ = normalize_with_mapping(current['end_text'])
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


SECTION_TUPLE_LEN = 2


def split_by_sections(
    documents: List[Document], model: BaseChatModel
) -> Tuple[List[Document], Dict[str, Any]]:
    """
    Fatia documentos em macro-seções. Retorna (docs_fatiados, metadados_secao).
    """
    raw_res = detect_sections_with_model(documents, model)
    if isinstance(raw_res, tuple) and len(raw_res) == SECTION_TUPLE_LEN:
        sections, first_window = raw_res
    elif isinstance(raw_res, list):
        sections, first_window = raw_res, ''
    else:
        sections, first_window = [], ''

    full_text = '\n'.join(doc.page_content for doc in documents)
    base_metadata = documents[0].metadata.copy() if documents else {}
    normalized_text, mapping = normalize_with_mapping(full_text)

    valid_sections = find_valid_sections(sections, normalized_text)
    sections_meta = build_sections_meta(sections, valid_sections, first_window)
    split_docs = slice_sections_from_text(
        valid_sections, full_text, normalized_text, mapping, base_metadata
    )
    return split_docs or documents, sections_meta


def apply_sections_to_chunks(
    chunks: List[Document],
    valid_sections: List[Dict[str, Any]],
    normalized_text: str,
) -> List[Document]:
    current_offset = 0
    for chunk in chunks:
        chunk_norm, _ = normalize_with_mapping(chunk.page_content)
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


def assign_sections_to_chunks(
    chunks: List[Document], model: BaseChatModel
) -> Tuple[List[Document], Dict[str, Any]]:
    """
    Identifica macro-seções e as carimba nos chunks de PDF.
    """
    raw_res = detect_sections_with_model(chunks, model)
    if isinstance(raw_res, tuple) and len(raw_res) == SECTION_TUPLE_LEN:
        sections, first_window = raw_res
    elif isinstance(raw_res, list):
        sections, first_window = raw_res, ''
    else:
        sections, first_window = [], ''

    full_text = '\n'.join(doc.page_content for doc in chunks)
    normalized_text, _ = normalize_with_mapping(full_text)

    valid_sections = find_valid_sections(sections, normalized_text)
    sections_meta = build_sections_meta(sections, valid_sections, first_window)
    assigned_chunks = apply_sections_to_chunks(
        chunks, valid_sections, normalized_text
    )
    return assigned_chunks, sections_meta


async def assign_sections_with_telemetry(
    chunks: List[Document],
    model: BaseChatModel,
    run_id: Optional[UUID] = None,
) -> List[Document]:
    """
    Executa a atribuição de seções registrando a etapa no RunLogger.
    """
    run_logger = get_run_logger()
    t_sec = datetime.now()
    if run_id:
        await run_logger.start_stage(run_id=run_id, stage='sections')
    try:
        formatted_docs, sections_meta = assign_sections_to_chunks(
            chunks, model
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


async def split_sections_with_telemetry(
    raw_docs: List[Document],
    model: BaseChatModel,
    run_id: Optional[UUID] = None,
) -> List[Document]:
    """
    Executa o fatiamento de seções em DOCX/TXT registrando no RunLogger.
    """
    run_logger = get_run_logger()
    t_sec = datetime.now()
    if run_id:
        await run_logger.start_stage(run_id=run_id, stage='sections')
    try:
        section_docs, sections_meta = split_by_sections(raw_docs, model)
        if run_id:
            d_sec = int((datetime.now() - t_sec).total_seconds() * 1000)
            await run_logger.complete_stage(
                run_id=run_id,
                stage='sections',
                duration_ms=d_sec,
                item_count=len(sections_meta.get('sections_detected', [])),
                data=sections_meta,
            )
        return section_docs
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
