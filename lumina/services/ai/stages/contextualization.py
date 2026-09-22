from dataclasses import dataclass
from typing import Optional

from langchain_core.documents import Document

from lumina.services.ai.stages.section_models import Section


@dataclass
class DocumentMetadata:
    """Metadados do documento de origem disponíveis para contextualização."""

    source_name: str


def generate_chunk_context(
    chunk: Document,
    section: Section,
    document_metadata: DocumentMetadata,
) -> Optional[str]:
    """
    Ponto de extensão para contextualização de chunk antes da geração de
    embedding.

    Objetivo futuro: usar um modelo de linguagem para gerar de 1 a 2
    frases de contexto situacional (documento, seção, papel semântico) e
    concatenar esse texto ao chunk antes da vetorização, sem alterar o
    texto enviado ao LLM na etapa de avaliação.

    Custo: chamada de LLM por chunk. Motivo de estar mockada nesta fase:
    impacto direto no tempo de processamento do documento, a ser avaliado
    separadamente antes de ativação.

    Estado atual: sem efeito. Retorna None. Chamada mantida no pipeline
    para que a ativação futura não exija alteração estrutural do fluxo
    de extração, apenas remoção deste mock.
    """
    # TODO: implementação futura — ver issue #12
    return None
