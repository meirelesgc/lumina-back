from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from lumina import prompts as PROMPTS
from lumina.core.dependencies import Model
from lumina.core.settings import SETTINGS
from lumina.schemas import DocumentReleaseFeedback
from lumina.schemas.processing_run import (
    CriterionEvaluationRecord,
    ProcessingStatus,
)
from lumina.services.ai.stages.citations import process_citations
from lumina.services.run_logger import get_run_logger

CHAIN_STEPS_COUNT = 3
MAX_RETRIES = 3


def get_evaluation_chain(model: Model):
    """
    Cria a chain LangChain com parser para DocumentReleaseFeedback.
    """
    parser = JsonOutputParser(pydantic_object=DocumentReleaseFeedback)
    fmt = {'format_instructions': parser.get_format_instructions()}
    prompt = PromptTemplate(
        template=PROMPTS.DOCUMENT_ANALYSIS_PROMPT,
        input_variables=[
            'document',
            'source',
            'requirement',
            'expected_section',
            'query',
        ],
        partial_variables=fmt,
    )
    return prompt | model | parser


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


def _build_criterion_record(
    item: dict,
    parsed: dict,
    meta: dict,
) -> CriterionEvaluationRecord:
    score_val = parsed.get('score')
    retrieval_data = {
        'query_executed': item.get('retriever_query', ''),
        'retrieved_chunks': (
            item.get('retrieved_chunks') or item.get('initial_chunks', [])
        ),
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
            item.get('expected_section') or item.get('query') or 'Critério'
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
    chunks = item.get('_chunks') or []
    provided, hallucinated, refs = process_citations(raw_citations, chunks)
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


async def evaluate_criteria_batch(
    chain: Any,
    eval_args: list[dict],
    run_id: Optional[UUID] = None,
) -> None:
    """
    Avalia concorrentemente os ramos da árvore com retentativas,
    isolamento de falhas de schema e rastreamento no RunLogger.
    """
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


# Alias para manter compatibilidade
apply_tree = evaluate_criteria_batch
