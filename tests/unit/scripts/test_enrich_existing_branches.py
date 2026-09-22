import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from lumina.schemas.branch import (
    BranchSectionRequirement,
    ExpansionType,
    QueryExpansionItem,
    QueryExpansionList,
    SectionRequirementScope,
)
from lumina.scripts.enrich_existing_branches import enrich_branch
from lumina.services.ai.branch_analyzer import BranchNormativeContext

EXPECTED_EXPANSIONS_COUNT_ONE = 1


def _context():
    return BranchNormativeContext(
        branch_title='Qualificação Técnica',
        branch_description='Exige comprovação da equipe executora.',
        taxonomy_title='Habilitação',
        typification_name='Edital',
    )


def _fake_session():
    session = MagicMock()
    session.commit = AsyncMock()
    return session


def _patch_common(
    mocker, branch_id, active_requirement=False, active_expansions=False
):
    session = _fake_session()

    @contextlib.asynccontextmanager
    async def _session_cm():
        yield session

    mocker.patch(
        'lumina.scripts.enrich_existing_branches.async_session', _session_cm
    )
    mocker.patch(
        'lumina.scripts.enrich_existing_branches.'
        'branch_section_requirement_repo.get_active_grouped',
        AsyncMock(
            return_value=(
                {branch_id: MagicMock()} if active_requirement else {}
            )
        ),
    )
    mocker.patch(
        'lumina.scripts.enrich_existing_branches.'
        'branch_query_expansion_repo.list_active_grouped',
        AsyncMock(
            return_value=(
                {branch_id: [MagicMock()]} if active_expansions else {}
            )
        ),
    )
    analyze_mock = mocker.patch(
        'lumina.scripts.enrich_existing_branches.'
        'analyze_branch_section_requirement',
        AsyncMock(
            return_value=BranchSectionRequirement(
                scope=SectionRequirementScope.SPECIFIC_SECTION,
                expected_section='Qualificação Técnica',
                reasoning='Exigência de atestado técnico.',
            )
        ),
    )
    generate_mock = mocker.patch(
        'lumina.scripts.enrich_existing_branches.generate_query_expansions',
        AsyncMock(
            return_value=QueryExpansionList(
                expansions=[
                    QueryExpansionItem(
                        expansion_text='Formulação alternativa',
                        expansion_type=ExpansionType.PARAPHRASE,
                    )
                ]
            )
        ),
    )
    persist_req_mock = mocker.patch(
        'lumina.scripts.enrich_existing_branches.'
        'persist_branch_section_requirement',
        AsyncMock(),
    )
    persist_exp_mock = mocker.patch(
        'lumina.scripts.enrich_existing_branches.persist_branch_expansions',
        AsyncMock(),
    )
    return {
        'session': session,
        'analyze': analyze_mock,
        'generate': generate_mock,
        'persist_req': persist_req_mock,
        'persist_exp': persist_exp_mock,
    }


@pytest.mark.asyncio
async def test_enrich_branch_skips_when_already_enriched(mocker):
    branch_id = uuid4()
    mocks = _patch_common(
        mocker, branch_id, active_requirement=True, active_expansions=True
    )

    summary = await enrich_branch(
        branch_id=branch_id,
        context=_context(),
        semaphore=asyncio.Semaphore(1),
        index=1,
        total=1,
    )

    assert 'já ativo (skip)' in summary
    assert 'já ativas (skip)' in summary
    mocks['analyze'].assert_not_called()
    mocks['generate'].assert_not_called()
    mocks['persist_req'].assert_not_called()
    mocks['persist_exp'].assert_not_called()
    mocks['session'].commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_enrich_branch_generates_and_persists_when_missing(mocker):
    branch_id = uuid4()
    mocks = _patch_common(mocker, branch_id)

    summary = await enrich_branch(
        branch_id=branch_id,
        context=_context(),
        semaphore=asyncio.Semaphore(1),
        index=1,
        total=1,
    )

    assert 'SPECIFIC_SECTION' in summary
    assert f'expansions={EXPECTED_EXPANSIONS_COUNT_ONE}' in summary
    mocks['persist_req'].assert_called_once()
    mocks['persist_exp'].assert_called_once()
    mocks['session'].commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_enrich_branch_dry_run_calls_llm_but_does_not_persist(mocker):
    branch_id = uuid4()
    mocks = _patch_common(mocker, branch_id)

    await enrich_branch(
        branch_id=branch_id,
        context=_context(),
        semaphore=asyncio.Semaphore(1),
        index=1,
        total=1,
        dry_run=True,
    )

    mocks['analyze'].assert_called_once()
    mocks['generate'].assert_called_once()
    mocks['persist_req'].assert_not_called()
    mocks['persist_exp'].assert_not_called()
    mocks['session'].commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_enrich_branch_force_regenerates_even_if_active(mocker):
    branch_id = uuid4()
    mocks = _patch_common(
        mocker, branch_id, active_requirement=True, active_expansions=True
    )

    await enrich_branch(
        branch_id=branch_id,
        context=_context(),
        semaphore=asyncio.Semaphore(1),
        index=1,
        total=1,
        force=True,
    )

    mocks['analyze'].assert_called_once()
    mocks['generate'].assert_called_once()
    mocks['persist_req'].assert_called_once()
    mocks['persist_exp'].assert_called_once()
