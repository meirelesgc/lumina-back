import asyncio
import difflib
from typing import Any, List, Optional
from uuid import UUID

from langchain_core.documents import Document
from sqlalchemy.ext.asyncio import AsyncSession

from lumina import prompts as PROMPTS
from lumina.core.dependencies import VStore
from lumina.core.settings import Settings
from lumina.models import DocumentRelease, Typification
from lumina.schemas.branch import SectionRequirementScope
from lumina.schemas.typification import TypificationList
from lumina.services.ai.stages import reranking, vector_store_sql
from lumina.services.ai.stages.sections import SECTION_SUMMARY_RECORD_TYPE

SETTINGS = Settings()

MAX_CHUNKS = 5
RRF_K = 60

SECTION_ROUTING_TOP_SECTIONS = 2
SECTION_ROUTING_MAX_DISTANCE = 0.25

NEIGHBOR_WINDOW = 1
SMALL_SECTION_THRESHOLD = 4
MIN_OVERLAP_CHARS = 20
MERGE_OVERLAP_WINDOW_CHARS = 300

RERANK_CANDIDATE_K = 25


def get_base_filter(db_release: DocumentRelease) -> dict:
    """
    Filtro de isolamento por documento para busca normal de chunks.
    Exclui resumos de seção (Fase 2) via ausência do campo `record_type`,
    o que preserva compatibilidade com chunks indexados antes desta
    mudança (nunca tiveram o campo) sem exigir reingestão.
    """
    path = db_release.file_path.split('/')[-1]
    allowed_source = f'lumina/storage/uploads/{path}'
    return {
        'source': allowed_source,
        'record_type': {'$exists': False},
    }


def get_section_filter(base_filter: dict) -> dict:
    """Filtro que restringe a busca aos resumos de seção (Fase 2)."""
    return {
        'source': base_filter['source'],
        'record_type': SECTION_SUMMARY_RECORD_TYPE,
    }


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
    Funde múltiplas listas ranqueadas de chunks (consulta original,
    expansões da Fase 1 e busca léxica da Fase 4) por Reciprocal Rank
    Fusion, deduplicando por identidade de chunk. Com uma única lista de
    entrada o resultado é equivalente ao top-k original.
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


async def route_candidate_sections(
    vstore: VStore,
    query_text: str,
    section_filter: dict,
    top_sections: int = SECTION_ROUTING_TOP_SECTIONS,
    max_distance: float = SECTION_ROUTING_MAX_DISTANCE,
) -> Optional[List[str]]:
    """
    Busca as seções mais prováveis para um critério normativo entre os
    resumos de seção indexados (Fase 2). Retorna None quando nenhuma
    seção atinge o limiar de confiança (`max_distance`), sinalizando
    fallback para busca global irrestrita.
    """
    if not query_text or not query_text.strip():
        return None

    results = await vstore.asimilarity_search_with_score(
        query_text, k=top_sections, filter=section_filter
    )
    candidates = [
        doc.metadata.get('section_title')
        for doc, score in results
        if score <= max_distance and doc.metadata.get('section_title')
    ]
    return candidates or None


def _merge_overlapping_text(
    text_a: str,
    text_b: str,
    window: int = MERGE_OVERLAP_WINDOW_CHARS,
) -> str:
    """
    Mescla dois textos de chunks vizinhos removendo a sobreposição
    duplicada (produzida pelo `chunk_overlap` do splitter), casando o
    maior sufixo de `text_a` que é prefixo de `text_b`.
    """
    if not text_a:
        return text_b
    if not text_b:
        return text_a

    tail = text_a[-window:]
    head = text_b[:window]
    matcher = difflib.SequenceMatcher(None, tail, head)
    match = matcher.find_longest_match(0, len(tail), 0, len(head))

    is_true_overlap = (
        match.size >= MIN_OVERLAP_CHARS
        and match.a + match.size == len(tail)
        and match.b == 0
    )
    if is_true_overlap:
        return text_a + text_b[match.size :]
    return f'{text_a}\n{text_b}'


async def expand_and_merge_neighbors(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    chunks: List[Document],
    source: str,
    window: int = NEIGHBOR_WINDOW,
    small_section_threshold: int = SMALL_SECTION_THRESHOLD,
) -> List[Document]:
    """
    Expande cada chunk final com seus vizinhos na mesma seção/página
    (`chunk_index_in_section` ± window) e mescla o texto em um único
    bloco por âncora, eliminando duplicação (Fase 3). Quando a seção
    possui poucos chunks, usa a seção inteira em vez da janela.
    """
    merged_results: List[Document] = []
    seen_identities: set = set()

    for anchor in chunks:
        section_index = anchor.metadata.get('section_index')
        page = anchor.metadata.get('page')
        target_idx = anchor.metadata.get('chunk_index_in_section')

        if section_index is None or page is None or target_idx is None:
            merged_results.append(anchor)
            continue

        siblings = await vector_store_sql.fetch_chunk_siblings(
            session, source, section_index, page
        )
        if not siblings:
            merged_results.append(anchor)
            continue

        if len(siblings) <= small_section_threshold:
            selected = siblings
        else:
            lo, hi = target_idx - window, target_idx + window
            selected = [
                s
                for s in siblings
                if lo <= s.metadata.get('chunk_index_in_section', -1) <= hi
            ]
            if not selected:
                selected = [anchor]

        selected = sorted(
            selected,
            key=lambda d: d.metadata.get('chunk_index_in_section', 0),
        )

        identity = tuple(s.metadata.get('chunk_id') for s in selected)
        if identity in seen_identities:
            continue
        seen_identities.add(identity)

        merged_text = selected[0].page_content
        for sibling in selected[1:]:
            merged_text = _merge_overlapping_text(
                merged_text, sibling.page_content
            )

        all_rects = []
        for s in selected:
            all_rects.extend(s.metadata.get('rects', []) or [])

        merged_results.append(
            Document(
                page_content=merged_text,
                metadata={**anchor.metadata, 'rects': all_rects},
            )
        )

    return merged_results


async def retrieve_criteria_payload(  # noqa: PLR0913, PLR0917, PLR0914
    session: AsyncSession,
    vstore: VStore,
    taxonomy: dict,
    branch: dict,
    base_filter: dict,
    max_chunks: int = MAX_CHUNKS,
    expansions: Optional[List[str]] = None,
    section_requirement: Optional[dict] = None,
) -> dict:
    """
    Recupera e formata as evidências textuais para um único critério
    normativo: roteamento opcional por seção (Fase 2), busca vetorial
    (consulta original + expansões, Fase 1) fundida com busca léxica
    (Fase 4) via RRF, reranking opcional sobre um conjunto ampliado de
    candidatos (Fase 5, mockado) e expansão/merge de chunks vizinhos
    (Fase 3).
    """
    taxonomy_title = (taxonomy.get('title') or '').strip()
    b_title = (branch.get('title') or '').strip()
    b_desc = (branch.get('description') or '').strip()
    query_text = f'{b_title}: {b_desc}'
    query = PROMPTS.QUERY.format(section=taxonomy_title, query=query_text)

    queries = [query] + [
        PROMPTS.QUERY.format(section=taxonomy_title, query=expansion_text)
        for expansion_text in (expansions or [])
    ]

    # 0. Roteamento por seção (Fase 2)
    chunk_filter = base_filter
    is_specific_section = (
        section_requirement
        and section_requirement.get('scope')
        == SectionRequirementScope.SPECIFIC_SECTION.value
    )
    if is_specific_section:
        routing_query = (
            section_requirement.get('expected_section') or query_text
        )
        candidates = await route_candidate_sections(
            vstore, routing_query, get_section_filter(base_filter)
        )
        if candidates:
            chunk_filter = {
                **base_filter,
                'section_title': {'$in': candidates},
            }

    source = base_filter.get('source')
    k_search = (
        RERANK_CANDIDATE_K
        if SETTINGS.CROSS_ENCODER_RERANKING_ENABLED
        else max_chunks
    )

    # 1. Busca Semântica (original + expansões, em paralelo) + Léxica
    dense_lists = await asyncio.gather(*[
        vstore.asimilarity_search(q, k=k_search, filter=chunk_filter)
        for q in queries
    ])
    lexical_results = await vector_store_sql.lexical_search(
        session, query_text, source, k=k_search
    )
    fused_candidates = reciprocal_rank_fusion(
        [*dense_lists, lexical_results], top_n=k_search
    )

    # 2. Reranking opcional sobre candidatos ampliados (Fase 5, mockado)
    if SETTINGS.CROSS_ENCODER_RERANKING_ENABLED:
        reranked = reranking.rerank_chunks(
            query_text, fused_candidates, top_n=max_chunks
        )
        ranked_chunks = (
            reranked if reranked is not None else fused_candidates[:max_chunks]
        )
    else:
        ranked_chunks = fused_candidates[:max_chunks]

    # 3. Expansão de vizinhos e merge de janelas (Fase 3)
    evidence_chunks = await expand_and_merge_neighbors(
        session, ranked_chunks, source
    )

    retrieved_chunk_ids = [
        c.metadata.get('chunk_id') or str(getattr(c, 'id', ''))
        for c in evidence_chunks
        if c.metadata.get('chunk_id') or getattr(c, 'id', None)
    ]

    # 4. Consolidação de Metadados PII (Presidio Mapping)
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


async def retrieve_evaluation_payloads(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    vstore: VStore,
    tree: list[Typification],
    db_release: DocumentRelease,
    expansions_by_branch: Optional[dict[UUID, tuple[int, List[str]]]] = None,
    section_requirements_by_branch: Optional[dict[UUID, dict]] = None,
) -> list[dict]:
    """
    Percorre a árvore normativa em uma única passada, recuperando
    evidências diretamente para cada critério normativo, com roteamento
    por seção (Fase 2), fusão de consultas e busca híbrida (Fases 1 e 4),
    reranking opcional (Fase 5) e expansão de vizinhos (Fase 3).
    """
    payload = {'typifications': tree}
    eval_args = TypificationList.model_validate(payload).model_dump(
        mode='json'
    )
    base_filter = get_base_filter(db_release)
    expansions_by_branch = expansions_by_branch or {}
    section_requirements_by_branch = section_requirements_by_branch or {}
    payloads = []

    for typification in iter_typifications(eval_args):
        for taxonomy in iter_taxonomies(typification):
            for branch in iter_branches(taxonomy):
                branch_id = branch.get('id')
                branch_uuid = UUID(branch_id) if branch_id else None
                version, expansions = expansions_by_branch.get(
                    branch_uuid, (None, [])
                )
                section_requirement = section_requirements_by_branch.get(
                    branch_uuid
                )
                crit_payload = await retrieve_criteria_payload(
                    session,
                    vstore,
                    taxonomy,
                    branch,
                    base_filter,
                    expansions=expansions,
                    section_requirement=section_requirement,
                )
                crit_payload['expansion_generation_version'] = version
                crit_payload['section_requirement_version'] = (
                    section_requirement.get('generation_version')
                    if section_requirement
                    else None
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
