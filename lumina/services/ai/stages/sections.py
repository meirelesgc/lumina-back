from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from lumina.core.settings import Settings
from lumina.services.run_logger import get_run_logger

SETTINGS = Settings()
DEFAULT_SECTION_TITLE: str = 'NÃO ENCONTRADA'


class SectionInfo(BaseModel):
    section_name: str = Field(description='Nome normalizado da seção.')
    start_text: Optional[str] = Field(
        default=None,
        description=(
            'Trecho exato inicial da seção contendo entre 15 e 30 palavras.'
        ),
    )
    end_text: Optional[str] = Field(
        default=None,
        description=(
            'Trecho exato final da seção contendo entre 15 e 30 palavras.'
        ),
    )


class ChunkSections(BaseModel):
    sections: List[SectionInfo] = Field(default_factory=list)


def detect_sections_with_model(
    documents: List[Document], model: Optional[BaseChatModel] = None
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Stub de compatibilidade: retorna lista vazia de seções e string vazia.
    """
    return [], ''


def normalize_with_mapping(text: str) -> Tuple[str, List[int]]:
    """
    Stub de compatibilidade para mapeamento de normalização de texto.
    """
    return text.lower(), list(range(len(text)))


def assign_sections_to_chunks(
    chunks: List[Document], model: Optional[BaseChatModel] = None
) -> Tuple[List[Document], Dict[str, Any]]:
    """
    Atribui a macro-seção padrão "NÃO ENCONTRADA" a todos os chunks de PDF.
    """
    for chunk in chunks:
        chunk.metadata['section_title'] = DEFAULT_SECTION_TITLE
        chunk.page_content = (
            f'SECTION: {DEFAULT_SECTION_TITLE}\n\n{chunk.page_content}'
        )

    sections_meta: Dict[str, Any] = {
        'input_window_text': '',
        'sections_detected': [],
        'mapping_success_rate': 1.0,
        'default_assigned': DEFAULT_SECTION_TITLE,
    }
    return chunks, sections_meta


async def assign_sections_with_telemetry(
    chunks: List[Document],
    model: Optional[BaseChatModel] = None,
    run_id: Optional[UUID] = None,
) -> List[Document]:
    """
    Executa a atribuição padrão de seções registrando a etapa no RunLogger.
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
