from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from lumina.schemas.branch import (
    BranchSectionRequirement,
    SectionRequirementScope,
)
from lumina.services.ai.branch_analyzer import (
    BranchNormativeContext,
    analyze_branch_section_requirement,
    run_branch_section_analysis_background,
)


@pytest.mark.asyncio
async def test_analyze_branch_specific_section():
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        return_value=BranchSectionRequirement(
            scope=SectionRequirementScope.SPECIFIC_SECTION,
            expected_section='Habilitação Jurídica',
            reasoning='Regra referente a documentos de habilitação jurídica.',
        )
    )
    mock_llm.with_structured_output.return_value = mock_structured

    context = BranchNormativeContext(
        branch_title='Apresentação do Contrato Social',
        branch_description='Exige cópia autenticada do contrato social.',
        taxonomy_title='Habilitação',
        taxonomy_description='Critérios de habilitação e idoneidade.',
        typification_name='Edital de Pregão Eletrônico',
    )

    result = await analyze_branch_section_requirement(
        context=context, model=mock_llm
    )

    assert result.scope == SectionRequirementScope.SPECIFIC_SECTION
    assert result.expected_section == 'Habilitação Jurídica'
    assert 'habilitação' in result.reasoning.lower()


@pytest.mark.asyncio
async def test_analyze_branch_entire_document():
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        return_value=BranchSectionRequirement(
            scope=SectionRequirementScope.ENTIRE_DOCUMENT,
            expected_section=None,
            reasoning=(
                'Regra formal transversal a ser verificada em todo o texto.'
            ),
        )
    )
    mock_llm.with_structured_output.return_value = mock_structured

    context = BranchNormativeContext(
        branch_title='Ausência de Rasuras e Emendas',
        branch_description=(
            'O documento não pode conter rasuras em nenhuma página.'
        ),
        taxonomy_title='Requisitos Formais Gerais',
        typification_name='Edital',
    )

    result = await analyze_branch_section_requirement(
        context=context, model=mock_llm
    )

    assert result.scope == SectionRequirementScope.ENTIRE_DOCUMENT
    assert result.expected_section is None


@pytest.mark.asyncio
async def test_analyze_branch_fallback_on_exception():
    mock_llm = MagicMock()
    mock_llm.with_structured_output.side_effect = RuntimeError(
        'LLM API connection failure'
    )

    context = BranchNormativeContext(
        branch_title='Regra qualquer',
    )

    result = await analyze_branch_section_requirement(
        context=context, model=mock_llm
    )

    assert result.scope == SectionRequirementScope.UNKNOWN
    assert result.expected_section is None
    assert 'fallback' in result.reasoning.lower()


@pytest.mark.asyncio
async def test_run_branch_section_analysis_background_success():
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        return_value=BranchSectionRequirement(
            scope=SectionRequirementScope.SPECIFIC_SECTION,
            expected_section='Qualificação Técnica',
            reasoning='Exigência de atestado técnico.',
        )
    )
    mock_llm.with_structured_output.return_value = mock_structured

    branch_id = uuid4()
    context = BranchNormativeContext(
        branch_title='Atestado de Capacidade Técnica',
        taxonomy_title='Qualificação Técnica',
        typification_name='Edital',
    )

    result = await run_branch_section_analysis_background(
        branch_id=branch_id,
        context=context,
        model=mock_llm,
    )

    assert result is not None
    assert result.scope == SectionRequirementScope.SPECIFIC_SECTION
    assert result.expected_section == 'Qualificação Técnica'


@pytest.mark.asyncio
async def test_run_branch_section_analysis_background_handles_error():
    mock_llm = MagicMock()
    # Fallback seguro para UNKNOWN caso ocorra erro inesperado
    result = await run_branch_section_analysis_background(
        branch_id=uuid4(),
        context=BranchNormativeContext(branch_title='Branch Teste'),
        model=mock_llm,
    )

    # analyze_branch_section_requirement faz fallback para UNKNOWN, sem quebrar
    assert result is not None
    assert result.scope == SectionRequirementScope.UNKNOWN
