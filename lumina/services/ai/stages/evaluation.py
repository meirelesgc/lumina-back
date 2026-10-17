import random
from typing import Any

from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from lumina import prompts as PROMPTS
from lumina.core.dependencies import Model
from lumina.schemas import DocumentReleaseFeedback
from lumina.services.ai.stages.citations import process_citations

CHAIN_STEPS_COUNT = 3
MAX_RETRIES = 3


def with_low_verbosity(model: Model) -> Model:
    """
    Retorna uma cópia do modelo com verbosity='low' quando o modelo suporta
    o parâmetro, sem alterar a instância compartilhada com outros fluxos.
    """
    if 'verbosity' not in getattr(type(model), 'model_fields', {}):
        return model
    return model.model_copy(update={'verbosity': 'low'})


def select_evaluation_style() -> str:
    """
    Sorteia o bloco de estilo de resposta do parecer de um critério.
    """
    return random.choice(list(PROMPTS.EVALUATION_STYLES.values()))


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
            'style_instructions',
        ],
        partial_variables=fmt,
    )
    return prompt | with_low_verbosity(model) | parser


def _extract_raw_text(raw_resp: Any) -> str:
    """
    Texto da resposta do modelo. Modelos com raciocínio devolvem o conteúdo
    como lista de blocos, e `AIMessage.text` junta os blocos de texto.
    """
    if isinstance(raw_resp, BaseMessage):
        return raw_resp.text
    if hasattr(raw_resp, 'content'):
        return str(raw_resp.content)
    return str(raw_resp)


def _process_eval_item(item: dict, raw_resp: Any, parser_step: Any) -> None:
    if parser_step:
        raw_text = _extract_raw_text(raw_resp)
        try:
            parsed = parser_step.parse(raw_text)
        except Exception as err:
            parsed = {
                'fulfilled': False,
                'score': 0.0,
                'feedback': f'Erro na validação de schema: {err}',
                'citations': [],
            }
    else:
        parsed = raw_resp if isinstance(raw_resp, dict) else {}

    item.update(parsed)
    raw_citations = parsed.get('citations') or parsed.get('references') or []
    chunks = item.get('_chunks') or []
    _, _, refs = process_citations(raw_citations, chunks)
    item['references'] = refs


async def _execute_chain_batch(
    chain: Any,
    eval_args: list[dict],
    can_decompose: bool,
) -> tuple[list[Any], Any]:
    if can_decompose:
        prompt_step, model_step, parser_step = chain.steps
        prompt_and_model = prompt_step | model_step
        raw_responses = await prompt_and_model.abatch(eval_args)
        return raw_responses, parser_step

    raw_responses = await chain.abatch(eval_args)
    return raw_responses, None


async def evaluate_criteria_batch(chain: Any, eval_args: list[dict]) -> None:
    """
    Avalia concorrentemente os ramos da árvore com retentativas e
    isolamento de falhas de schema por critério. Itens com `skip_evaluation`
    já trazem o veredito e não vão ao modelo.
    """
    last_exception = None
    can_decompose = (
        hasattr(chain, 'steps')
        and isinstance(chain.steps, (list, tuple))
        and len(chain.steps) == CHAIN_STEPS_COUNT
    )
    pending = [item for item in eval_args if not item.get('skip_evaluation')]
    if not pending:
        return eval_args
    for item in pending:
        item['style_instructions'] = select_evaluation_style()

    for _ in range(MAX_RETRIES):
        try:
            raw_responses, parser_step = await _execute_chain_batch(
                chain, pending, can_decompose
            )
            for item, raw_resp in zip(pending, raw_responses):
                _process_eval_item(item, raw_resp, parser_step)
            return eval_args
        except Exception as e:
            last_exception = e

    if last_exception:
        raise last_exception


# Alias para manter compatibilidade
apply_tree = evaluate_criteria_batch
