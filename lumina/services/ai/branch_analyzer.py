import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import PromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.core.database import async_session
from lumina.core.llm import get_fast_model
from lumina.models import (
    BranchSectionRequirement as BranchSectionRequirementModel,
)
from lumina.repositories import branch_section_requirement_repo
from lumina.schemas.branch import (
    BranchSectionRequirement,
    SectionRequirementScope,
)

logger = logging.getLogger(__name__)


@dataclass
class BranchNormativeContext:
    """Contexto normativo da tríade (Tipificação, Taxonomia, Ramo)."""

    branch_title: str
    branch_description: Optional[str] = None
    taxonomy_title: Optional[str] = None
    taxonomy_description: Optional[str] = None
    typification_name: Optional[str] = None


BRANCH_ANALYSIS_PROMPT = (
    'Você analisa critérios de avaliação de documentos acadêmicos e '
    'técnicos: artigos, revisões sistemáticas, anteprojetos e relatórios '
    'técnicos.\n\n'
    'Analise a estrutura do critério (Tipificação, Taxonomia e Ramo) e '
    'determine se a verificação exige a busca em uma SEÇÃO ESPECÍFICA do '
    'documento, se deve analisar o DOCUMENTO INTEIRO, ou se NÃO FOI '
    'POSSÍVEL IDENTIFICAR.\n\n'
    '### Estrutura do Critério em Análise:\n'
    '- **Tipificação Documental:** {typification_name}\n'
    '- **Taxonomia / Grupo:** {taxonomy_title} ({taxonomy_description})\n'
    '- **Ramo / Critério Específico:** {branch_title}\n'
    '  **Descrição:** {branch_description}\n\n'
    '### Diretrizes de Avaliação:\n'
    'Use a tipificação para decidir quais seções o documento costuma ter. '
    'Os títulos da taxonomia e do ramo nomeiam o critério e em geral não '
    'aparecem no documento. Seções típicas por tipo de documento:\n'
    '- Anteprojeto: Introdução, Problema de Pesquisa, Objetivos, '
    'Justificativa, Metodologia, Cronograma, Referências.\n'
    '- Revisão sistemática: Resumo, Introdução, Métodos, Resultados, '
    'Discussão, Conclusão, Referências.\n'
    '- Artigo: Resumo, Introdução, Trabalhos Relacionados, Metodologia, '
    'Resultados, Discussão, Conclusão, Referências.\n'
    '- Relatório técnico: Resumo, Introdução, Desenvolvimento, Resultados, '
    'Conclusão, Referências.\n\n'
    "1. Retorne 'SPECIFIC_SECTION' só se uma única seção do tipo de "
    'documento informado concentra o conteúdo exigido (ex: objetivo geral '
    'em Objetivos, procedimentos de coleta em Metodologia). Neste caso, '
    "forneça em 'expected_section' o título dessa seção, como listado "
    'acima. A busca fica restrita a essa seção: uma seção errada esconde a '
    'evidência.\n'
    "2. Retorne 'ENTIRE_DOCUMENT' se o critério for transversal e deva ser "
    'observado ao longo de todo o texto (ex: clareza e objetividade da '
    'redação, coerência entre objetivos e conclusões, padronização das '
    'citações) ou se o conteúdo puder aparecer em mais de uma seção (ex: '
    'revisão da literatura e lacunas, que podem estar na Introdução, na '
    'Justificativa ou no Problema de Pesquisa).\n'
    "3. Retorne 'UNKNOWN' se a descrição for excessivamente vaga, "
    'incompleta ou inconclusiva para determinar a localização.\n'
)


async def analyze_branch_section_requirement(
    context: BranchNormativeContext,
    model: Optional[BaseChatModel] = None,
) -> BranchSectionRequirement:
    """Analisa a tríade normativa com LLM rápido e infere o escopo de busca."""
    llm = model or get_fast_model()
    prompt = PromptTemplate.from_template(BRANCH_ANALYSIS_PROMPT).format(
        typification_name=context.typification_name or 'Não informada',
        taxonomy_title=context.taxonomy_title or 'Não informada',
        taxonomy_description=context.taxonomy_description or '',
        branch_title=context.branch_title or '',
        branch_description=context.branch_description or '',
    )

    try:
        if hasattr(llm, 'with_structured_output'):
            structured_llm = llm.with_structured_output(
                BranchSectionRequirement
            )
            result = await structured_llm.ainvoke(prompt)
            if isinstance(result, BranchSectionRequirement):
                return result
    except Exception as err:
        logger.warning('Falha na chamada LLM de análise de seção: %s', err)

    return BranchSectionRequirement(
        scope=SectionRequirementScope.UNKNOWN,
        expected_section=None,
        reasoning='Classificação indeterminada (fallback).',
    )


async def persist_branch_section_requirement(
    session: AsyncSession,
    branch_id: UUID,
    requirement: BranchSectionRequirement,
    generation_model: str,
    user_id: Optional[UUID] = None,
) -> None:
    """Desativa a análise anterior e persiste a nova versão ativa."""
    previous_version = (
        await branch_section_requirement_repo.get_latest_generation_version(
            session, branch_id
        )
    )
    await branch_section_requirement_repo.deactivate_active(session, branch_id)

    db_requirement = BranchSectionRequirementModel(
        branch_id=branch_id,
        scope=requirement.scope.value,
        expected_section=requirement.expected_section,
        reasoning=requirement.reasoning,
        generation_model=generation_model,
        generation_version=previous_version + 1,
        is_active=True,
    )
    db_requirement.set_creation_audit(user_id)
    branch_section_requirement_repo.add(session, db_requirement)
    await session.flush()


async def run_branch_section_analysis_background(
    branch_id: UUID,
    context: BranchNormativeContext,
    model: Optional[BaseChatModel] = None,
) -> Optional[BranchSectionRequirement]:
    """Executado em background task após a criação/atualização do branch.

    Analisa o escopo de busca do critério e persiste o resultado
    (Fase 2 — roteamento por seção), para uso no motor de recuperação.
    """
    try:
        requirement = await analyze_branch_section_requirement(
            context=context,
            model=model,
        )
        llm = model or get_fast_model()

        async with async_session() as session:
            await persist_branch_section_requirement(
                session=session,
                branch_id=branch_id,
                requirement=requirement,
                generation_model=getattr(llm, 'model_name', 'unknown'),
            )
            await session.commit()

        logger.info(
            'Branch %s analisada com sucesso: scope=%s, expected_section=%s',
            branch_id,
            requirement.scope,
            requirement.expected_section,
        )
        return requirement
    except Exception as e:
        logger.error(
            'Erro na background task de análise do branch %s: %s',
            branch_id,
            e,
        )
        return None
