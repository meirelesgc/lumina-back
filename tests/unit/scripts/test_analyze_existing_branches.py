import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from lumina.models import Branch, Taxonomy, Typification
from lumina.schemas.branch import (
    BranchSectionRequirement,
    SectionRequirementScope,
)
from lumina.scripts.analyze_existing_branches import (
    process_single_branch,
    run_analysis,
)


@pytest.mark.asyncio
async def test_process_single_branch_dry_run():
    branch = MagicMock(spec=Branch)
    branch.id = uuid4()
    branch.title = 'Regra Teste Dry-Run'
    branch.description = 'Descricao da regra teste'
    branch.taxonomy_id = uuid4()
    branch.taxonomy = MagicMock(spec=Taxonomy)
    branch.taxonomy.title = 'Taxonomia Teste'
    branch.taxonomy.description = 'Desc Taxonomia'
    branch.taxonomy.typification = MagicMock(spec=Typification)
    branch.taxonomy.typification.name = 'Edital Teste'

    semaphore = asyncio.Semaphore(1)
    result = await process_single_branch(
        branch=branch,
        semaphore=semaphore,
        index=1,
        total=1,
        dry_run=True,
    )

    assert result['scope'] == 'DRY_RUN'
    assert result['branch_title'] == 'Regra Teste Dry-Run'
    assert result['taxonomy_title'] == 'Taxonomia Teste'
    assert result['typification_name'] == 'Edital Teste'


@pytest.mark.asyncio
async def test_process_single_branch_live():
    branch = MagicMock(spec=Branch)
    branch.id = uuid4()
    branch.title = 'Regra Jurídica'
    branch.description = 'Descricao juridica'
    branch.taxonomy_id = uuid4()
    branch.taxonomy = MagicMock(spec=Taxonomy)
    branch.taxonomy.title = 'Jurídico'
    branch.taxonomy.description = 'Desc Jurídico'
    branch.taxonomy.typification = MagicMock(spec=Typification)
    branch.taxonomy.typification.name = 'Edital'

    semaphore = asyncio.Semaphore(1)

    with patch(
        'lumina.scripts.analyze_existing_branches.analyze_branch_section_requirement',
        new_callable=AsyncMock,
    ) as mock_analyze:
        mock_analyze.return_value = BranchSectionRequirement(
            scope=SectionRequirementScope.SPECIFIC_SECTION,
            expected_section='Habilitação Jurídica',
            reasoning='Regra de qualificação jurídica.',
        )

        result = await process_single_branch(
            branch=branch,
            semaphore=semaphore,
            index=1,
            total=1,
            dry_run=False,
        )

        assert result['scope'] == 'SPECIFIC_SECTION'
        assert result['expected_section'] == 'Habilitação Jurídica'


@pytest.mark.asyncio
async def test_run_analysis_with_output(tmp_path):
    output_file = tmp_path / 'analysis.json'

    branch = MagicMock(spec=Branch)
    branch.id = uuid4()
    branch.title = 'Regra Objeto'
    branch.description = 'Descricao objeto'
    branch.taxonomy_id = uuid4()
    branch.taxonomy = MagicMock(spec=Taxonomy)
    branch.taxonomy.title = 'Objeto'
    branch.taxonomy.description = 'Desc'
    branch.taxonomy.typification = None

    mock_session = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.unique.return_value = [branch]
    mock_session.scalars.return_value = mock_scalars

    mock_async_session = MagicMock()
    mock_async_session.return_value.__aenter__.return_value = mock_session

    with (
        patch(
            'lumina.scripts.analyze_existing_branches.async_session',
            mock_async_session,
        ),
        patch(
            'lumina.scripts.analyze_existing_branches.analyze_branch_section_requirement',
            new_callable=AsyncMock,
        ) as mock_analyze,
    ):
        mock_analyze.return_value = BranchSectionRequirement(
            scope=SectionRequirementScope.SPECIFIC_SECTION,
            expected_section='Termo de Referência',
            reasoning='Objeto da licitação.',
        )

        results = await run_analysis(
            output_path=str(output_file),
            limit=5,
            concurrency=2,
            dry_run=False,
        )

        assert len(results) == 1
        assert results[0]['expected_section'] == 'Termo de Referência'
        assert output_file.exists()

        saved_data = json.loads(output_file.read_text(encoding='utf-8'))
        assert len(saved_data) == 1
        assert saved_data[0]['branch_title'] == 'Regra Objeto'
