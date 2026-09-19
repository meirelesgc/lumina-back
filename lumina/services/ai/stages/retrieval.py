from typing import Any, List

from langchain_core.documents import Document

from lumina import prompts as PROMPTS
from lumina.core.dependencies import VStore
from lumina.models import DocumentRelease, Typification
from lumina.schemas.typification import TypificationList

MAX_CHUNKS = 5


def get_base_filter(db_release: DocumentRelease) -> dict:
    path = db_release.file_path.split('/')[-1]
    allowed_source = f'lumina/storage/uploads/{path}'
    return {'source': allowed_source}


def iter_typifications(eval_args: dict):
    for typification in eval_args.get('typifications') or []:
        yield typification


def iter_taxonomies(typification: dict):
    for taxonomy in typification.get('taxonomies') or []:
        yield taxonomy


def iter_branches(taxonomy: dict):
    for branch in taxonomy.get('branches') or []:
        yield branch


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
        content = getattr(
            doc, 'page_content', getattr(doc, 'content', str(doc))
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


async def retrieve_criteria_payload(
    vstore: VStore,
    taxonomy: dict,
    branch: dict,
    base_filter: dict,
    max_chunks: int = MAX_CHUNKS,
) -> dict:
    """
    Recupera e formata as evidências textuais para um único critério normativo
    usando busca vetorial direta (single-stage retrieval).
    """
    taxonomy_title = (taxonomy.get('title') or '').strip()
    b_title = (branch.get('title') or '').strip()
    b_desc = (branch.get('description') or '').strip()
    query_text = f'{b_title}: {b_desc}'
    query = PROMPTS.QUERY.format(section=taxonomy_title, query=query_text)

    # 1. Busca Semântica Direta
    evidence_chunks = await vstore.asimilarity_search(
        query, k=max_chunks, filter=base_filter
    )
    retrieved_chunk_ids = [
        c.metadata.get('chunk_id') or str(getattr(c, 'id', ''))
        for c in evidence_chunks
        if c.metadata.get('chunk_id') or getattr(c, 'id', None)
    ]

    # 2. Consolidação de Metadados PII (Presidio Mapping)
    full_mapping: dict = {}
    for d in evidence_chunks:
        current_mapping = d.metadata.get('presidio_mapping') or {}
        for category, entities in current_mapping.items():
            if category not in full_mapping:
                full_mapping[category] = {}
            full_mapping[category].update(entities)

    formatted_doc = format_context(evidence_chunks)
    sources = taxonomy.get('sources') or []
    source_names = ', '.join([
        s.get('name', '')
        if isinstance(s, dict)
        else getattr(s, 'name', str(s))
        for s in sources
    ])

    return {
        'id': branch.get('id'),
        'document': formatted_doc,
        'source': source_names,
        'requirement': (
            f'{b_title}: {b_desc}'
            if b_title and b_desc
            else (b_title or b_desc)
        ),
        'expected_section': taxonomy_title,
        'query': f"Analise o item '{b_title}' na seção '{taxonomy_title}'.",
        'presidio_mapping': full_mapping,
        '_chunks': evidence_chunks,
        'retriever_query': query,
        'retrieved_chunks': retrieved_chunk_ids,
    }


async def retrieve_evaluation_payloads(
    vstore: VStore, tree: list[Typification], db_release: DocumentRelease
) -> list[dict]:
    """
    Percorre a árvore normativa em uma única passada, recuperando
    evidências diretamente para cada critério normativo.
    """
    payload = {'typifications': tree}
    eval_args = TypificationList.model_validate(payload).model_dump(
        mode='json'
    )
    base_filter = get_base_filter(db_release)
    payloads = []

    for typification in iter_typifications(eval_args):
        for taxonomy in iter_taxonomies(typification):
            for branch in iter_branches(taxonomy):
                crit_payload = await retrieve_criteria_payload(
                    vstore, taxonomy, branch, base_filter
                )
                if crit_payload['document']:
                    payloads.append(crit_payload)

    return payloads


def build_chunk_prompts(chunks: List[Document]) -> List[str]:
    prompts_list = []
    for chunk in chunks:
        chunk_id = chunk.metadata.get('chunk_id', 'unknown_id')
        section = chunk.metadata.get('section_title', '')
        conteudo = chunk.page_content

        if '\n\n' in conteudo and conteudo.startswith('SECTION:'):
            conteudo = conteudo.split('\n\n', 1)[1]

        prompt = (
            f'[FONTE] chunk_id: {chunk_id}\n'
            f'SECTION: {section}\n'
            f'{conteudo.strip()}'
        )
        prompts_list.append(prompt)
    return prompts_list
