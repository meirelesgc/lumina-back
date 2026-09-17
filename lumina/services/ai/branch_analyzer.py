import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import PromptTemplate

from lumina.core.llm import get_fast_model
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
    'Você é um especialista em análise de conformidade de editais e '
    'instrumentos convocatórios.\n\n'
    'Analise a estrutura normativa fornecida (Tipificação, Taxonomia e '
    'Ramo) e determine se o cumprimento desta regra exige a busca em uma '
    'SEÇÃO ESPECÍFICA do documento, se deve analisar o DOCUMENTO INTEIRO, '
    'ou se NÃO FOI POSSÍVEL IDENTIFICAR.\n\n'
    '### Estrutura Normativa em Análise:\n'
    '- **Tipificação Documental:** {typification_name}\n'
    '- **Taxonomia / Grupo:** {taxonomy_title} ({taxonomy_description})\n'
    '- **Ramo / Regra Específica:** {branch_title}\n'
    '  **Descrição:** {branch_description}\n\n'
    '### Diretrizes de Avaliação:\n'
    "1. Retorne 'SPECIFIC_SECTION' se a regra tratar de itens que possuem "
    'seção formal própria e típica em documentos convocatórios (ex: '
    "'Habilitação Jurídica', 'Qualificação Técnica', 'Termo de Referência', "
    "'Proposta de Preços', 'Sanções Administrativas'). Neste caso, forneça "
    "em 'expected_section' o nome normalizado sugerido da seção.\n"
    "2. Retorne 'ENTIRE_DOCUMENT' se a regra for transversal, formal ou "
    'principiológica, devendo ser observada ao longo de todo o arquivo '
    '(ex: clareza e precisão da redação geral, ausência de rasuras, '
    'conformidade com a ABNT, assinaturas eletrônicas válidas em todo o '
    'texto, cláusulas de integridade e anticorrupção gerais).\n'
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


async def run_branch_section_analysis_background(
    branch_id: UUID,
    context: BranchNormativeContext,
    model: Optional[BaseChatModel] = None,
) -> Optional[BranchSectionRequirement]:
    """Executado em background task após a criação do branch.

    Processa a análise e registra o resultado em log, sem efeitos colaterais.
    """
    try:
        requirement = await analyze_branch_section_requirement(
            context=context,
            model=model,
        )
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
