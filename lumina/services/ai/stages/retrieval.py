from typing import Any, List

from langchain_core.documents import Document

from lumina.models import DocumentRelease
from lumina.services.ai.stages.sentences import mark_sentences

MAX_CHUNKS = 5
RRF_K = 60


def get_base_filter(db_release: DocumentRelease) -> dict:
    """Filtro de isolamento por documento para a busca de chunks."""
    path = db_release.file_path.split('/')[-1]
    allowed_source = f'lumina/storage/uploads/{path}'
    return {'source': allowed_source}


def format_context(branch_or_chunks: Any) -> str:
    """
    Formata blocos de evidência recuperados em string de contexto com
    delimitação visual por seção e identificadores de chunk [FONTE].
    """
    if isinstance(branch_or_chunks, dict):
        chunks = (
            branch_or_chunks.get('evidence_chunks')
            or branch_or_chunks.get('_chunks')
            or []
        )
    else:
        chunks = branch_or_chunks or []

    chunks_list = list(chunks)
    chunks_list.sort(key=lambda x: x.metadata.get('chunk_index', 0))
    formatted_parts = []
    current_section = None

    for doc in chunks_list:
        section_title = doc.metadata.get('section_title', '').strip()
        content = mark_sentences(
            getattr(doc, 'page_content', getattr(doc, 'content', str(doc))),
            doc.metadata.get('sentences'),
        )
        header_pattern = f'SECTION: {section_title}\n\n'

        if content.startswith(header_pattern):
            clean_text = content[len(header_pattern) :]
        else:
            clean_text = content

        if section_title != current_section:
            if current_section is not None:
                formatted_parts.append('\n\n---\n\n')
            if section_title:
                formatted_parts.append(
                    f'## CONTEXTO DA SEÇÃO: {section_title}\n'
                )
            current_section = section_title

        chunk_id = doc.metadata.get('chunk_id', 'unknown_id')
        formatted_parts.append(f'[FONTE] chunk_id: {chunk_id}\n{clean_text}')

    return ''.join(formatted_parts).strip()


def _chunk_identity(doc: Document) -> str:
    """Identificador estável de um chunk para deduplicação em fusões."""
    return (
        doc.metadata.get('chunk_id')
        or str(getattr(doc, 'id', '') or '')
        or doc.page_content
    )


def reciprocal_rank_fusion(
    result_lists: List[List[Document]],
    k: int = RRF_K,
    top_n: int = MAX_CHUNKS,
) -> List[Document]:
    """
    Funde múltiplas listas ranqueadas de chunks (busca densa e léxica) por
    Reciprocal Rank Fusion, deduplicando por identidade de chunk. Com uma
    única lista de entrada o resultado é equivalente ao top-k original.
    """
    scores: dict[str, float] = {}
    representative: dict[str, Document] = {}

    for result_list in result_lists:
        for rank, doc in enumerate(result_list, start=1):
            identity = _chunk_identity(doc)
            scores[identity] = scores.get(identity, 0.0) + 1.0 / (k + rank)
            representative.setdefault(identity, doc)

    ranked_ids = sorted(scores, key=lambda i: scores[i], reverse=True)
    return [representative[identity] for identity in ranked_ids[:top_n]]


def build_chunk_prompts(chunks: List[Document]) -> List[str]:
    prompts_list = []
    for chunk in chunks:
        chunk_id = chunk.metadata.get('chunk_id', 'unknown_id')
        section = chunk.metadata.get('section_title', '')
        conteudo = mark_sentences(
            chunk.page_content, chunk.metadata.get('sentences')
        )

        if '\n\n' in conteudo and conteudo.startswith('SECTION:'):
            conteudo = conteudo.split('\n\n', 1)[1]

        prompt = (
            f'[FONTE] chunk_id: {chunk_id}\n'
            f'SECTION: {section}\n'
            f'{conteudo.strip()}'
        )
        prompts_list.append(prompt)
    return prompts_list
