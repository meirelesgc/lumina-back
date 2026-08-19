from uuid import uuid4

import pytest

from lumina.models import Advisorship, User
from lumina.repositories import advisorship_repo
from lumina.schemas.advisorship import AdvisorshipFilter
from lumina.schemas.user import AccessType


@pytest.mark.asyncio
async def test_advisorship_repo_crud_and_queries(session):
    # 1. Create 2 users
    advisor = User(
        username=f'advisor_{uuid4().hex[:6]}',
        email=f'advisor_{uuid4().hex[:6]}@test.com',
        phone_number=f'55019{uuid4().int % 100000000:08d}',
        password='hash',
        access_level=AccessType.DEFAULT,
    )
    advisee = User(
        username=f'advisee_{uuid4().hex[:6]}',
        email=f'advisee_{uuid4().hex[:6]}@test.com',
        phone_number=f'55019{uuid4().int % 100000000:08d}',
        password='hash',
        access_level=AccessType.DEFAULT,
    )
    session.add_all([advisor, advisee])
    await session.commit()
    await session.refresh(advisor)
    await session.refresh(advisee)

    # 2. Add advisorship
    advisorship = Advisorship(
        advisor_id=advisor.id,
        advisee_id=advisee.id,
        role_type='MAIN_ADVISOR',
        topic='Pesquisa em LLMs',
        status='ACTIVE',
    )
    advisorship_repo.add_advisorship(session, advisorship)
    await session.commit()
    await session.refresh(advisorship)

    # 3. Get by id
    fetched = await advisorship_repo.get_by_id(session, advisorship.id)
    assert fetched is not None
    assert fetched.id == advisorship.id
    assert fetched.advisor_id == advisor.id
    assert fetched.advisee_id == advisee.id

    # 4. Get active pair
    pair = await advisorship_repo.get_active_pair(
        session, advisor.id, advisee.id, role_type='MAIN_ADVISOR'
    )
    assert pair is not None
    assert pair.id == advisorship.id

    # 5. List by advisor
    by_advisor = await advisorship_repo.list_by_advisor(session, advisor.id)
    assert len(by_advisor) >= 1
    assert by_advisor[0].advisee_id == advisee.id

    # 6. List by advisee
    by_advisee = await advisorship_repo.list_by_advisee(session, advisee.id)
    assert len(by_advisee) >= 1
    assert by_advisee[0].advisor_id == advisor.id

    # 7. List all with filter
    filters = AdvisorshipFilter(advisor_id=advisor.id, limit=10, offset=0)
    all_filtered = await advisorship_repo.list_all(session, filters)
    assert len(all_filtered) >= 1
