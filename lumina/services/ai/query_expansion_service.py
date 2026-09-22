import logging
from typing import Optional
from uuid import UUID

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import PromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.core.database import async_session
from lumina.core.llm import get_fast_model
from lumina.models import BranchQueryExpansion
from lumina.repositories import branch_query_expansion_repo
from lumina.schemas.branch import QueryExpansionItem, QueryExpansionList
from lumina.services.ai.branch_analyzer import BranchNormativeContext

logger = logging.getLogger(__name__)

MIN_EXPANSIONS = 2
MAX_EXPANSIONS = 4

EXPANSION_PROMPT = (
    'Você é um especialista em recuperação de informação (RAG) para '
    'documentos de conformidade normativa.\n\n'
    'A partir do critério normativo abaixo, gere de 2 a 4 formulações '
    'alternativas de consulta para busca vetorial, capazes de recuperar '
    'trechos relevantes que a formulação original poderia não capturar.\n\n'
    '### Critério em Análise:\n'
    '- **Tipificação Documental:** {typification_name}\n'
    '- **Taxonomia / Grupo:** {taxonomy_title} ({taxonomy_description})\n'
    '- **Ramo / Regra:** {branch_title}\n'
    '  **Descrição:** {branch_description}\n\n'
    '### Diretrizes:\n'
    "1. Gere reformulações semânticas (tipo 'paraphrase'): mesma intenção, "
    'vocabulário e estrutura diferentes.\n'
    '2. Quando o critério envolver múltiplos aspectos, gere sub-perguntas '
    "(tipo 'sub_question') que decompõem a verificação em partes menores.\n"
    '3. Se houver uma dica clara de seção do documento onde a informação '
    "costuma aparecer, gere uma formulação do tipo 'section_hint' apontando "
    'para esse contexto.\n'
    '4. Não repita a formulação original nem gere variações redundantes '
    'entre si.\n'
)


async def generate_query_expansions(
    context: BranchNormativeContext,
    model: Optional[BaseChatModel] = None,
) -> QueryExpansionList:
    """Gera formulações alternativas de consulta via LLM rápido."""
    llm = model or get_fast_model()
    prompt = PromptTemplate.from_template(EXPANSION_PROMPT).format(
        typification_name=context.typification_name or 'Não informada',
        taxonomy_title=context.taxonomy_title or 'Não informada',
        taxonomy_description=context.taxonomy_description or '',
        branch_title=context.branch_title or '',
        branch_description=context.branch_description or '',
    )

    try:
        if hasattr(llm, 'with_structured_output'):
            structured_llm = llm.with_structured_output(QueryExpansionList)
            result = await structured_llm.ainvoke(prompt)
            if isinstance(result, QueryExpansionList):
                return result
    except Exception as err:
        logger.warning('Falha na chamada LLM de query expansion: %s', err)

    return QueryExpansionList(expansions=[])


async def persist_branch_expansions(
    session: AsyncSession,
    branch_id: UUID,
    expansions: list[QueryExpansionItem],
    generation_model: str,
    user_id: Optional[UUID] = None,
) -> None:
    """Desativa expansões anteriores e persiste a nova geração ativa."""
    previous_version = (
        await branch_query_expansion_repo.get_latest_generation_version(
            session, branch_id
        )
    )
    await branch_query_expansion_repo.deactivate_active(session, branch_id)

    next_version = previous_version + 1
    for item in expansions:
        db_expansion = BranchQueryExpansion(
            branch_id=branch_id,
            expansion_text=item.expansion_text,
            expansion_type=item.expansion_type.value,
            generation_model=generation_model,
            generation_version=next_version,
            is_active=True,
        )
        db_expansion.set_creation_audit(user_id)
        branch_query_expansion_repo.add(session, db_expansion)

    await session.flush()


async def run_branch_query_expansion_background(
    branch_id: UUID,
    context: BranchNormativeContext,
    model: Optional[BaseChatModel] = None,
) -> None:
    """Executado em background após criação/atualização do branch.

    Gera e persiste as expansões de consulta de forma idempotente e
    isolada, sem impactar o caminho de avaliação.
    """
    try:
        llm = model or get_fast_model()
        result = await generate_query_expansions(context=context, model=llm)
        if not result.expansions:
            return

        async with async_session() as session:
            await persist_branch_expansions(
                session=session,
                branch_id=branch_id,
                expansions=result.expansions,
                generation_model=getattr(llm, 'model_name', 'unknown'),
            )
            await session.commit()

        logger.info(
            'Expansões de consulta geradas para branch %s: %d itens',
            branch_id,
            len(result.expansions),
        )
    except Exception as e:
        logger.error(
            'Erro na background task de query expansion do branch %s: %s',
            branch_id,
            e,
        )
