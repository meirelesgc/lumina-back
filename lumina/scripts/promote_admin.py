import asyncio
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from lumina.core.database import async_session
from lumina.models import User
from lumina.repositories import user_repo
from lumina.schemas import AccessType


async def promote(session: AsyncSession, email: str) -> User:
    user = await user_repo.get_by_email(session, email)
    if not user or user.deleted_at:
        raise ValueError(f'Nenhuma conta ativa com o e-mail {email}.')

    user.access_level = AccessType.ADMIN
    await session.commit()
    return user


async def run(email: str) -> None:
    async with async_session() as session:
        await promote(session, email)


def main():
    if len(sys.argv) != 2:
        sys.exit('Uso: python -m lumina.scripts.promote_admin <email>')
    try:
        asyncio.run(run(sys.argv[1]))
    except ValueError as error:
        sys.exit(str(error))


if __name__ == '__main__':
    main()
