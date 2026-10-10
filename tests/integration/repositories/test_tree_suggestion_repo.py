from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.models import TreeSuggestionItem, TreeSuggestionSession
from lumina.repositories import tree_suggestion_repo
from lumina.schemas.tree_suggestion import TreeSuggestionFilter


async def _create_session(
    session: AsyncSession, status: str = 'ready'
) -> TreeSuggestionSession:
    suggestion_session = TreeSuggestionSession(
        mode='create',
        file_path='/uploads/norma.pdf',
        original_filename='norma.pdf',
        status=status,
    )
    tree_suggestion_repo.add_session(session, suggestion_session)
    await session.flush()
    return suggestion_session


def _item(session_id, kind, position, parent=None, status='pending'):
    return TreeSuggestionItem(
        session_id=session_id,
        kind=kind,
        operation='create',
        proposed_title=f'{kind} {position}',
        position=position,
        status=status,
        parent_item_id=parent.id if parent else None,
    )


async def _create_tree(session: AsyncSession, session_id):
    typ = _item(session_id, 'typification', 0)
    tree_suggestion_repo.add_items(session, [typ])
    await session.flush()
    tax = _item(session_id, 'taxonomy', 1, typ)
    tree_suggestion_repo.add_items(session, [tax])
    await session.flush()
    branch_pending = _item(session_id, 'branch', 2, tax)
    branch_discarded = _item(session_id, 'branch', 3, tax, 'discarded')
    tree_suggestion_repo.add_items(session, [branch_pending, branch_discarded])
    await session.flush()
    return typ, tax, branch_pending, branch_discarded


@pytest.mark.asyncio
async def test_get_session_loads_items_in_order(session: AsyncSession):
    suggestion_session = await _create_session(session)
    await _create_tree(session, suggestion_session.id)
    await session.commit()
    session.expunge_all()

    result = await tree_suggestion_repo.get_session(
        session, suggestion_session.id
    )

    assert result is not None
    assert [item.position for item in result.items] == [0, 1, 2, 3]


@pytest.mark.asyncio
async def test_list_sessions_filters_by_status(session: AsyncSession):
    ready = await _create_session(session, 'ready')
    await _create_session(session, 'failed')
    await session.commit()

    result = await tree_suggestion_repo.list_sessions(
        session, TreeSuggestionFilter(status='ready')
    )

    assert ready.id in {s.id for s in result}
    assert all(s.status == 'ready' for s in result)


@pytest.mark.asyncio
async def test_list_pending_descendant_ids(session: AsyncSession):
    suggestion_session = await _create_session(session)
    typ, tax, branch_pending, _ = await _create_tree(
        session, suggestion_session.id
    )

    result = await tree_suggestion_repo.list_pending_descendant_ids(
        session, typ.id
    )

    assert set(result) == {tax.id, branch_pending.id}


@pytest.mark.asyncio
async def test_mark_discarded_and_count_pending(session: AsyncSession, user):
    suggestion_session = await _create_session(session)
    typ, tax, branch_pending, _ = await _create_tree(
        session, suggestion_session.id
    )
    assert (
        await tree_suggestion_repo.count_pending(
            session, suggestion_session.id
        )
        == 3  # noqa: PLR2004
    )

    await tree_suggestion_repo.mark_discarded(
        session, [tax.id, branch_pending.id], user.id, datetime.now()
    )

    assert (
        await tree_suggestion_repo.count_pending(
            session, suggestion_session.id
        )
        == 1
    )
    assert tax.status == 'discarded'
    assert tax.reviewed_by == user.id


@pytest.mark.asyncio
async def test_get_item_for_update_scoped_to_session(session: AsyncSession):
    suggestion_session = await _create_session(session)
    other_session = await _create_session(session)
    typ, *_ = await _create_tree(session, suggestion_session.id)

    found = await tree_suggestion_repo.get_item_for_update(
        session, suggestion_session.id, typ.id
    )
    not_found = await tree_suggestion_repo.get_item_for_update(
        session, other_session.id, typ.id
    )

    assert found is not None
    assert not_found is None
