from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from lumina.repositories import branch_query_expansion_repo
from lumina.schemas.branch import (
    ExpansionType,
    QueryExpansionItem,
    QueryExpansionList,
)
from lumina.services.ai.branch_analyzer import BranchNormativeContext
from lumina.services.ai.query_expansion_service import (
    generate_query_expansions,
    persist_branch_expansions,
    run_branch_query_expansion_background,
)
from tests.factories.branch_factory import (
    BranchFactory,
    TaxonomyFactory,
    TypificationFactory,
)

EXPECTED_EXPANSIONS_COUNT_TWO = 2
EXPECTED_GENERATION_VERSION_TWO = 2


def _mock_llm_returning(result) -> MagicMock:
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=result)
    mock_llm.with_structured_output.return_value = mock_structured
    mock_llm.model_name = 'mock-model'
    return mock_llm


@pytest.mark.asyncio
async def test_generate_query_expansions_success():
    expected = QueryExpansionList(
        expansions=[
            QueryExpansionItem(
                expansion_text='Existe comprovação de qualificação técnica?',
                expansion_type=ExpansionType.PARAPHRASE,
            ),
            QueryExpansionItem(
                expansion_text='A equipe possui certificados válidos?',
                expansion_type=ExpansionType.SUB_QUESTION,
            ),
        ]
    )
    mock_llm = _mock_llm_returning(expected)

    context = BranchNormativeContext(
        branch_title='Qualificação Técnica',
        branch_description='Exige comprovação da equipe executora.',
        taxonomy_title='Habilitação',
        typification_name='Edital',
    )

    result = await generate_query_expansions(context=context, model=mock_llm)

    assert len(result.expansions) == EXPECTED_EXPANSIONS_COUNT_TWO
    assert result.expansions[0].expansion_type == ExpansionType.PARAPHRASE


@pytest.mark.asyncio
async def test_generate_query_expansions_fallback_on_exception():
    mock_llm = MagicMock()
    mock_llm.with_structured_output.side_effect = RuntimeError('LLM offline')

    result = await generate_query_expansions(
        context=BranchNormativeContext(branch_title='Regra qualquer'),
        model=mock_llm,
    )

    assert result.expansions == []


@pytest.mark.asyncio
async def test_generate_query_expansions_fallback_on_wrong_type():
    """Global test fixture mocks with_structured_output returning an
    unrelated schema (BranchSectionRequirement); must fall back safely."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=object())
    mock_llm.with_structured_output.return_value = mock_structured

    result = await generate_query_expansions(
        context=BranchNormativeContext(branch_title='Regra qualquer'),
        model=mock_llm,
    )

    assert result.expansions == []


@pytest.mark.asyncio
async def test_persist_branch_expansions_versions_and_deactivates(
    session, user
):
    typification = TypificationFactory()
    typification.set_creation_audit(user.id)
    session.add(typification)
    await session.commit()

    taxonomy = TaxonomyFactory(typification_id=typification.id)
    taxonomy.set_creation_audit(user.id)
    session.add(taxonomy)
    await session.commit()

    branch = BranchFactory(taxonomy_id=taxonomy.id)
    branch.set_creation_audit(user.id)
    session.add(branch)
    await session.commit()

    first_batch = [
        QueryExpansionItem(
            expansion_text='Primeira versão',
            expansion_type=ExpansionType.PARAPHRASE,
        )
    ]
    await persist_branch_expansions(
        session, branch.id, first_batch, generation_model='mock-model'
    )
    await session.flush()

    second_batch = [
        QueryExpansionItem(
            expansion_text='Segunda versão A',
            expansion_type=ExpansionType.PARAPHRASE,
        ),
        QueryExpansionItem(
            expansion_text='Segunda versão B',
            expansion_type=ExpansionType.SUB_QUESTION,
        ),
    ]
    await persist_branch_expansions(
        session, branch.id, second_batch, generation_model='mock-model'
    )
    await session.flush()

    grouped = await branch_query_expansion_repo.list_active_grouped(
        session, [branch.id]
    )
    active = grouped.get(branch.id, [])

    assert len(active) == EXPECTED_EXPANSIONS_COUNT_TWO
    assert all(
        e.generation_version == EXPECTED_GENERATION_VERSION_TWO for e in active
    )


@pytest.mark.asyncio
async def test_run_branch_query_expansion_background_handles_error():
    mock_llm = MagicMock()
    mock_llm.with_structured_output.side_effect = RuntimeError('boom')

    # Fallback vazio não gera nenhuma escrita e não propaga exceção.
    await run_branch_query_expansion_background(
        branch_id=uuid4(),
        context=BranchNormativeContext(branch_title='Branch Teste'),
        model=mock_llm,
    )
