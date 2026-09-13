from typing import Any, List

from langchain_core.documents import Document
from sqlalchemy import select

from lumina import prompts as PROMPTS
from lumina.core.dependencies import VStore
from lumina.models import DocumentRelease, Typification
from lumina.schemas.typification import TypificationList

MAX_CHUNKS = 3
MARGIN_SIZE = 2


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


async def fetch_chunks_by_indices(
    vstore: VStore, source: str, indices: list[int]
) -> list[Document]:
    if not indices:
        return []

    if hasattr(vstore, '_make_async_session') and hasattr(
        vstore, 'EmbeddingStore'
    ):
        try:
            async with vstore._make_async_session() as session:
                collection = await vstore.aget_collection(session)
                if not collection:
                    return []

                EmbeddingStore = vstore.EmbeddingStore
                source_filter = EmbeddingStore.cmetadata[
                    'source'
                ].astext == str(source)
                indices_str = [str(i) for i in indices]
                index_filter = EmbeddingStore.cmetadata[
                    'chunk_index'
                ].astext.in_(indices_str)

                stmt = select(EmbeddingStore).filter(
                    EmbeddingStore.collection_id == collection.uuid,
                    source_filter,
                    index_filter,
                )
                results = (await session.execute(stmt)).scalars().all()
                return [
                    Document(
                        id=str(r.id),
                        page_content=r.document,
                        metadata=r.cmetadata,
                    )
                    for r in results
                ]
        except Exception:
            pass

    # Fallback para mocks ou stores sem _make_async_session
    filter_dict = {
        'source': source,
        'chunk_index': {'$in': indices},
    }
    return await vstore.asimilarity_search(
        '', k=len(indices), filter=filter_dict
    )


async def get_expanded_chunks(
    vstore: VStore, original_chunks: list, margin_size: int = MARGIN_SIZE
) -> list[Document]:
    docs_indices_map = {}
    for chunk in original_chunks:
        source = chunk.metadata.get('source')
        current_idx = chunk.metadata.get('chunk_index')
        if source is None or current_idx is None:
            continue
        if source not in docs_indices_map:
            docs_indices_map[source] = set()

        start = max(0, current_idx - margin_size)
        end = current_idx + margin_size + 1
        for i in range(start, end):
            docs_indices_map[source].add(i)

    expanded_chunks = []
    for source, indices_set in docs_indices_map.items():
        indices_list = list(indices_set)
        found_chunks = await fetch_chunks_by_indices(
            vstore, source, indices_list
        )
        expanded_chunks.extend(found_chunks)

    if expanded_chunks:
        expanded_chunks.sort(key=lambda x: x.metadata.get('chunk_index', 0))

    return expanded_chunks


async def get_branch_sessions(
    vstore: VStore,
    eval_args: dict,
    base_filter: dict,
    max_chunks: int = MAX_CHUNKS,
):
    for typification in iter_typifications(eval_args):
        for taxonomy in iter_taxonomies(typification):
            taxonomy_title = taxonomy.get('title')
            for branch in iter_branches(taxonomy):
                t_title = (taxonomy_title or '').strip()
                b_title = (branch.get('title') or '').strip()
                b_desc = (branch.get('description') or '').strip()
                query_text = f'{b_title}: {b_desc}'
                query = PROMPTS.QUERY.format(section=t_title, query=query_text)
                chunks = await vstore.asimilarity_search(
                    query, k=max_chunks, filter=base_filter
                )
                branch['sessions'] = chunks
                branch['retriever_query'] = query
                branch['initial_chunks'] = [
                    c.metadata.get('chunk_id') or str(getattr(c, 'id', ''))
                    for c in chunks
                    if c.metadata.get('chunk_id') or getattr(c, 'id', None)
                ]


async def expand_branch_sessions(vstore: VStore, eval_args: dict):
    for typification in iter_typifications(eval_args):
        for taxonomy in iter_taxonomies(typification):
            for branch in iter_branches(taxonomy):
                original_chunks = branch.get('sessions', [])
                if not original_chunks:
                    continue

                expanded_chunks = await get_expanded_chunks(
                    vstore, original_chunks
                )

                if expanded_chunks:
                    branch['sessions'] = expanded_chunks
                    branch['expanded_chunks'] = [
                        c.metadata.get('chunk_id') or str(getattr(c, 'id', ''))
                        for c in expanded_chunks
                        if c.metadata.get('chunk_id') or getattr(c, 'id', None)
                    ]
                else:
                    branch['expanded_chunks'] = list(
                        branch.get('initial_chunks', [])
                    )


def format_context(branch: dict) -> str:
    sessions = branch.get('sessions') or []
    sessions.sort(key=lambda x: x.metadata.get('chunk_index', 0))
    formatted_parts = []
    current_section = None
    for doc in sessions:
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
                    f'## CONTEXTO DA SESSÃO: {section_title}\n'
                )
            current_section = section_title

        chunk_id = doc.metadata.get('chunk_id', 'unknown_id')
        formatted_parts.append(f'[FONTE] chunk_id: {chunk_id}\n{clean_text}')
    return ''.join(formatted_parts).strip()


def create_eval_payload(taxonomy: dict, branch: dict) -> dict:
    expected_session = taxonomy.get('title', '').strip()
    req_title = branch.get('title', '').strip()
    req_desc = branch.get('description', '').strip()

    sources = taxonomy.get('sources') or []
    source_names = ', '.join([getattr(s, 'name', str(s)) for s in sources])

    sessions = branch.get('sessions') or []
    full_mapping = {}
    for d in sessions:
        current_mapping = d.metadata.get('presidio_mapping') or {}
        for category, entities in current_mapping.items():
            if category not in full_mapping:
                full_mapping[category] = {}
            full_mapping[category].update(entities)

    return {
        'document': format_context(branch),
        'source': source_names,
        'requirement': f'{req_title}: {req_desc}'
        if req_title and req_desc
        else (req_title or req_desc),
        'expected_session': expected_session,
        'query': (
            f"Analise o item '{req_title}' na seção '{expected_session}'."
        ),
        'presidio_mapping': full_mapping,
        '_sessions': sessions,
        'retriever_query': branch.get('retriever_query', ''),
        'initial_chunks': branch.get('initial_chunks', []),
        'expanded_chunks': branch.get('expanded_chunks', []),
    }


async def get_eval_args(
    vstore: VStore, tree: list[Typification], db_release: DocumentRelease
) -> dict:
    payload = {'typifications': tree}
    eval_args = TypificationList.model_validate(payload).model_dump(
        mode='json'
    )
    base_filter = get_base_filter(db_release)
    await get_branch_sessions(vstore, eval_args, base_filter)
    await expand_branch_sessions(vstore, eval_args)
    return eval_args


async def simplify_eval_args(eval_args: dict) -> list[dict]:
    payloads = []
    for typification in iter_typifications(eval_args):
        for taxonomy in iter_taxonomies(typification):
            for branch in iter_branches(taxonomy):
                payload = create_eval_payload(taxonomy, branch)
                if payload['document']:
                    payload['id'] = branch.get('id')
                    payloads.append(payload)
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


async def retrieve_branch_context(
    vstore: VStore, db_release: DocumentRelease, query: str
) -> tuple[List[str], List[Any]]:
    if not query:
        return [], []

    base_filter = get_base_filter(db_release)
    original_chunks = await vstore.asimilarity_search(
        query, k=5, filter=base_filter
    )
    if not original_chunks:
        return [], []

    expanded_chunks = await get_expanded_chunks(vstore, original_chunks)
    return build_chunk_prompts(expanded_chunks), expanded_chunks
