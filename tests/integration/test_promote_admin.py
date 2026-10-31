import pytest

from lumina.schemas import AccessType
from lumina.scripts.promote_admin import promote


@pytest.mark.asyncio
async def test_operador_promove_conta(session, user):
    await promote(session, user.email)

    await session.refresh(user)
    assert user.access_level == AccessType.ADMIN


@pytest.mark.asyncio
async def test_email_inexistente_falha(session):
    with pytest.raises(ValueError, match='ninguem@lumina.test'):
        await promote(session, 'ninguem@lumina.test')
