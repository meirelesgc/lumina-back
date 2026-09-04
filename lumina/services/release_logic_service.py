from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from langchain_core.documents import Document
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from sqlalchemy import select

from lumina import prompts as PROMPTS
from lumina.core.dependencies import Model, VStore
from lumina.core.settings import SETTINGS
from lumina.models import DocumentRelease, Typification
from lumina.schemas import DocumentReleaseFeedback
from lumina.schemas.ai import Citation
from lumina.schemas.processing_run import (
    CriterionEvaluationRecord,
    ProcessingStatus,
)
from lumina.schemas.typification import TypificationList
from lumina.services.run_logger import get_run_logger

MAX_CHUNKS = 3
MARGIN_SIZE = 2

# --- Funções de Iteração e Filtros ---


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


# --- Funções de Busca Vetorial ---


async def _fetch_chunks_by_indices(
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

    # Fallback para mocks em testes ou stores sem _make_async_session
    filter_dict = {
        'source': source,
        'chunk_index': {'$in': indices},
    }
    return await vstore.asimilarity_search(
        '', k=len(indices), filter=filter_dict
    )


async def get_expanded_chunks(vstore: VStore, original_chunks: list) -> list:
    docs_indices_map = {}
    for chunk in original_chunks:
        source = chunk.metadata.get('source')
        current_idx = chunk.metadata.get('chunk_index')
        if source is None or current_idx is None:
            continue
        if source not in docs_indices_map:
            docs_indices_map[source] = set()

        start = max(0, current_idx - MARGIN_SIZE)
        end = current_idx + MARGIN_SIZE + 1
        for i in range(start, end):
            docs_indices_map[source].add(i)

    expanded_chunks = []
    for source, indices_set in docs_indices_map.items():
        indices_list = list(indices_set)
        found_chunks = await _fetch_chunks_by_indices(
            vstore, source, indices_list
        )
        expanded_chunks.extend(found_chunks)

    if expanded_chunks:
        expanded_chunks.sort(key=lambda x: x.metadata.get('chunk_index', 0))

    return expanded_chunks


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


async def get_eval_args(
    vstore: VStore, tree: list[Typification], db_release: DocumentRelease
):
    payload = {'typifications': tree}
    eval_args = TypificationList.model_validate(payload).model_dump(
        mode='json'
    )
    base_filter = get_base_filter(db_release)
    await get_branch_sessions(vstore, eval_args, base_filter)
    await expand_branch_sessions(vstore, eval_args)
    return eval_args


def get_chain(model: Model):
    parser = JsonOutputParser(pydantic_object=DocumentReleaseFeedback)
    fmt = {'format_instructions': parser.get_format_instructions()}
    prompt = PromptTemplate(
        template=PROMPTS.DOCUMENT_ANALYSIS_PROMPT,
        input_variables=[
            'document',
            'source',
            'requirement',
            'expected_session',
            'query',
        ],
        partial_variables=fmt,
    )
    return prompt | model | parser


def _format_context(branch: dict) -> str:
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


def _create_eval_payload(taxonomy: dict, branch: dict) -> dict:
    expected_session = taxonomy.get('title', '').strip()
    req_title = branch.get('title', '').strip()
    req_desc = branch.get('description', '').strip()

    sources = taxonomy.get('sources') or []
    source_names = ', '.join([getattr(s, 'name', str(s)) for s in sources])

    # Presidio mapping recovery
    sessions = branch.get('sessions') or []
    full_mapping = {}
    for d in sessions:
        current_mapping = d.metadata.get('presidio_mapping') or {}
        for category, entities in current_mapping.items():
            if category not in full_mapping:
                full_mapping[category] = {}
            full_mapping[category].update(entities)

    return {
        'document': _format_context(branch),
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


async def simplify_eval_args(eval_args: dict) -> list[dict]:
    payloads = []
    for typification in iter_typifications(eval_args):
        for taxonomy in iter_taxonomies(typification):
            for branch in iter_branches(taxonomy):
                payload = _create_eval_payload(taxonomy, branch)
                if payload['document']:
                    payload['id'] = branch.get('id')
                    payloads.append(payload)
    return payloads


CHAIN_STEPS_COUNT = 3
MAX_RETRIES = 3


def _extract_raw_output_and_tokens(
    raw_resp: Any,
) -> tuple[str, Optional[int], Optional[int]]:
    if hasattr(raw_resp, 'content'):
        raw_text = str(raw_resp.content)
    else:
        raw_text = str(raw_resp)

    tokens_prompt = None
    tokens_completion = None
    usage = getattr(raw_resp, 'usage_metadata', None)
    if not usage and hasattr(raw_resp, 'response_metadata'):
        meta = raw_resp.response_metadata or {}
        usage = meta.get('token_usage') or meta.get('usage')
    if isinstance(usage, dict):
        tokens_prompt = usage.get('input_tokens') or usage.get('prompt_tokens')
        tokens_completion = usage.get('output_tokens') or usage.get(
            'completion_tokens'
        )
    return raw_text, tokens_prompt, tokens_completion


def _process_citations(
    raw_citations: list, sessions: list
) -> tuple[list[str], list[str], list[dict]]:
    from lumina.services.ai_service import (  # noqa: PLC0415
        resolve_citations,
    )

    valid_chunk_ids = set()
    for d in sessions:
        cid = d.metadata.get('chunk_id') if hasattr(d, 'metadata') else None
        if not cid and hasattr(d, 'id'):
            cid = str(d.id)
        if cid:
            valid_chunk_ids.add(str(cid))

    provided: list[str] = []
    hallucinated: list[str] = []
    valid_objs: list[Citation] = []

    for c in raw_citations:
        cid = None
        if isinstance(c, dict):
            cid = str(c.get('chunk_id') or '')
            if cid in valid_chunk_ids:
                valid_objs.append(Citation(**c))
            elif cid:
                hallucinated.append(cid)
        elif isinstance(c, Citation):
            cid = str(c.chunk_id or '')
            if cid in valid_chunk_ids:
                valid_objs.append(c)
            elif cid:
                hallucinated.append(cid)
        if cid:
            provided.append(cid)

    resolved_refs = resolve_citations(valid_objs, sessions)
    return provided, hallucinated, resolved_refs


def partition_synthesis_text(text: str) -> dict[str, str]:
    if not text:
        return {
            'greeting': '',
            'fulfilled_points': '',
            'improvement_points': '',
            'final_guidance': '',
        }

    h_fulfilled = '# Pontos atendidos'
    h_improve = '# Pontos a aprimorar'
    h_final = '# Orientação final'

    lower_text = text.lower()
    idx_f = lower_text.find(h_fulfilled.lower())
    idx_i = lower_text.find(h_improve.lower())
    idx_g = lower_text.find(h_final.lower())

    greeting = ''
    fulfilled = ''
    improve = ''
    final = ''

    if idx_f != -1:
        greeting = text[:idx_f].strip()
        next_idx = (
            idx_i
            if idx_i != -1 and idx_i > idx_f
            else (idx_g if idx_g != -1 and idx_g > idx_f else len(text))
        )
        fulfilled = text[idx_f + len(h_fulfilled) : next_idx].strip()
    else:
        greeting = text.strip()

    if idx_i != -1:
        next_idx = idx_g if idx_g != -1 and idx_g > idx_i else len(text)
        improve = text[idx_i + len(h_improve) : next_idx].strip()

    if idx_g != -1:
        final = text[idx_g + len(h_final) :].strip()

    return {
        'greeting': greeting,
        'fulfilled_points': fulfilled,
        'improvement_points': improve,
        'final_guidance': final,
    }


def _build_criterion_record(
    item: dict,
    parsed: dict,
    meta: dict,
) -> CriterionEvaluationRecord:
    score_val = parsed.get('score')
    retrieval_data = {
        'query_executed': item.get('retriever_query', ''),
        'initial_chunks': item.get('initial_chunks', []),
        'expanded_chunks': item.get('expanded_chunks', []),
    }
    p_rendered = item.get('prompt', '') if SETTINGS.DEBUG_PIPELINE_RUNS else ''
    r_output = meta['raw_text'] if SETTINGS.DEBUG_PIPELINE_RUNS else ''
    interaction_data = {
        'model': meta['model_name'],
        'prompt_rendered': p_rendered,
        'raw_output': r_output,
        'tokens_prompt': meta['tok_prompt'],
        'tokens_completion': meta['tok_comp'],
        'schema_validation_error': meta['schema_err'],
    }
    output_data = {
        'fulfilled': bool(parsed.get('fulfilled', False)),
        'score': float(score_val) if score_val is not None else 0.0,
        'feedback': str(parsed.get('feedback') or ''),
        'citations_provided': meta['provided'],
        'citations_hallucinated': meta['hallucinated'],
    }
    crit_status = (
        ProcessingStatus.FAILED
        if meta['schema_err']
        else ProcessingStatus.COMPLETED
    )
    return CriterionEvaluationRecord(
        criterion_id=str(item.get('id') or ''),
        title=str(
            item.get('expected_session') or item.get('query') or 'Critério'
        ),
        status=crit_status,
        duration_ms=meta['avg_dur'],
        score=float(score_val) if score_val is not None else None,
        citations_count=len(meta['refs']),
        feedback=parsed.get('feedback'),
        error_message=meta['schema_err'],
        retrieval=retrieval_data,
        llm_interaction=interaction_data,
        llm_output=output_data,
    )


async def _process_eval_item(
    item: dict,
    raw_resp: Any,
    parser_step: Any,
    meta: dict,
) -> None:
    schema_err = None
    if parser_step:
        raw_text, tok_prompt, tok_comp = _extract_raw_output_and_tokens(
            raw_resp
        )
        try:
            parsed = parser_step.parse(raw_text)
        except Exception as err:
            schema_err = str(err)
            parsed = {
                'fulfilled': False,
                'score': 0.0,
                'feedback': f'Erro na validação de schema: {err}',
                'citations': [],
            }
    else:
        raw_text = str(raw_resp)
        tok_prompt = None
        tok_comp = None
        parsed = raw_resp if isinstance(raw_resp, dict) else {}

    item.update(parsed)
    raw_citations = parsed.get('citations') or parsed.get('references') or []
    sessions = item.get('_sessions') or []
    provided, hallucinated, refs = _process_citations(raw_citations, sessions)
    item['references'] = refs
    item['citations_provided'] = provided
    item['citations_hallucinated'] = hallucinated

    run_id = meta.get('run_id')
    if run_id:
        crit_meta = {
            'model_name': meta['model_name'],
            'raw_text': raw_text,
            'tok_prompt': tok_prompt,
            'tok_comp': tok_comp,
            'schema_err': schema_err,
            'avg_dur': meta['avg_dur'],
            'provided': provided,
            'hallucinated': hallucinated,
            'refs': refs,
        }
        crit_rec = _build_criterion_record(item, parsed, crit_meta)
        run_logger = get_run_logger()
        await run_logger.record_criterion(
            run_id=run_id,
            stage='evaluation',
            criterion_record=crit_rec,
        )


async def _execute_chain_batch(
    chain: Any,
    eval_args: list[dict],
    can_decompose: bool,
) -> tuple[list[Any], str, Any]:
    if can_decompose:
        prompt_step = chain.steps[0]
        model_step = chain.steps[1]
        parser_step = chain.steps[2]
        model_name = getattr(
            model_step,
            'model_name',
            getattr(model_step, 'model', 'unknown'),
        )
        prompt_and_model = prompt_step | model_step
        raw_responses = await prompt_and_model.abatch(eval_args)
        return raw_responses, model_name, parser_step

    raw_responses = await chain.abatch(eval_args)
    return raw_responses, 'unknown', None


async def apply_tree(
    chain: Any,
    eval_args: list[dict],
    run_id: Optional[UUID] = None,
):
    last_exception = None
    prompt_tpl = PROMPTS.DOCUMENT_ANALYSIS_PROMPT
    can_decompose = (
        hasattr(chain, 'steps')
        and isinstance(chain.steps, (list, tuple))
        and len(chain.steps) == CHAIN_STEPS_COUNT
    )

    for _ in range(MAX_RETRIES):
        try:
            t_batch = datetime.now()
            (
                raw_responses,
                model_name,
                parser_step,
            ) = await _execute_chain_batch(chain, eval_args, can_decompose)
            batch_dur = int((datetime.now() - t_batch).total_seconds() * 1000)
            avg_dur = max(1, batch_dur // max(1, len(eval_args)))

            for item, raw_resp in zip(eval_args, raw_responses):
                item['prompt'] = prompt_tpl.format(
                    **item, format_instructions=''
                )
                meta = {
                    'run_id': run_id,
                    'model_name': model_name,
                    'avg_dur': avg_dur,
                }
                await _process_eval_item(item, raw_resp, parser_step, meta)

            return eval_args
        except Exception as e:
            last_exception = e
    if last_exception:
        raise last_exception


def generate_description_prompt(eval_args: list[dict]) -> str:
    sorted_data = sorted(eval_args, key=lambda x: x['score'], reverse=True)
    top_results = sorted_data[:2]
    bottom_results = sorted_data[-2:]

    def format_items(items):
        text = ''
        for item in items:
            text += f'- Item: {item.get("query")}\n'
            text += f'  Nota: {item.get("score")}\n'
            status_str = (
                'Contemplado' if item.get('fulfilled') else 'Não contemplado'
            )
            text += f'  Status: {status_str}\n'
            text += f'  Feedback: {item.get("feedback")}\n\n'
        return text

    return PROMPTS.DESCRIPTION.format(
        top_text=format_items(top_results),
        bottom_text=format_items(bottom_results),
    ).strip()
