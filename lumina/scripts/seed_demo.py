import asyncio
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.core.database import async_session
from lumina.core.security import get_password_hash
from lumina.models import AccessType, Advisorship, Document, Project, User


async def _seed_users(session: AsyncSession) -> dict[str, User]:
    password_hash = get_password_hash('testtest')
    users_to_create = [
        {
            'email': 'aluno_advisee@universidade.edu.br',
            'username': 'aluno_advisee',
            'phone_number': '5511999990001',
            'name': 'Aluno / Orientando (João)',
        },
        {
            'email': 'advisor@universidade.edu.br',
            'username': 'prof_advisor',
            'phone_number': '5511999990002',
            'name': 'Prof. Orientador (Dr. Silva)',
        },
        {
            'email': 'stranger@teste.com',
            'username': 'stranger_user',
            'phone_number': '5511999990003',
            'name': 'Usuário Terceiro (Sem Vínculo)',
        },
    ]

    users_db = {}
    for u in users_to_create:
        stmt = select(User).where(User.email == u['email'])
        existing = await session.scalar(stmt)
        if not existing:
            user = User(
                username=u['username'],
                email=u['email'],
                password=password_hash,
                phone_number=u['phone_number'],
                access_level=AccessType.DEFAULT,
            )
            session.add(user)
            await session.flush()
            users_db[u['email']] = user
            print(f"  ✓ Usuário criado: {u['email']}")
        else:
            users_db[u['email']] = existing
            print(f"  · Usuário já existe: {u['email']}")

    return users_db


async def _seed_advisorship(
    session: AsyncSession, advisor: User, student: User
) -> None:
    stmt = select(Advisorship).where(
        Advisorship.advisor_id == advisor.id,
        Advisorship.advisee_id == student.id,
        Advisorship.status == 'ACTIVE',
    )
    if not await session.scalar(stmt):
        advisorship = Advisorship(
            advisor_id=advisor.id,
            advisee_id=student.id,
            role_type='MAIN_ADVISOR',
            topic='Pesquisa Aplicada em IA',
            status='ACTIVE',
        )
        session.add(advisorship)
        await session.flush()
        print('  ✓ Vínculo de orientação criado (Prof. Silva -> Aluno)')
    else:
        print('  · Vínculo de orientação já existe')


async def _seed_projects(
    session: AsyncSession, student: User, advisor: User, stranger: User
) -> None:
    projects_data = [
        (
            'Projeto TCC - Machine Learning Aplicado',
            'Projeto de conclusão de curso do aluno orientado.',
            student.id,
        ),
        (
            'Projeto de Pesquisa do Laboratório',
            'Projeto de pesquisa liderado pelo orientador.',
            advisor.id,
        ),
        (
            'Projeto Privado e Isolado',
            'Projeto de um usuário terceiro independente.',
            stranger.id,
        ),
    ]

    for p_name, p_desc, owner_id in projects_data:
        stmt = select(Project).where(
            Project.name == p_name, Project.deleted_at.is_(None)
        )
        if not await session.scalar(stmt):
            p = Project(name=p_name, description=p_desc)
            p.set_creation_audit(owner_id)
            session.add(p)
            print(f'  ✓ Projeto criado: {p_name}')
        else:
            print(f'  · Projeto já existe: {p_name}')


async def _seed_documents(
    session: AsyncSession, student: User, advisor: User, stranger: User
) -> None:
    docs_data = [
        (
            'Monografia - Versão Preliminar',
            f'MONO-{uuid4().hex[:6].upper()}',
            'Capítulos 1 e 2 submetidos para revisão.',
            student.id,
        ),
        (
            'Artigo Científico do Laboratório',
            f'ART-{uuid4().hex[:6].upper()}',
            'Artigo submetido para conferência.',
            advisor.id,
        ),
        (
            'Documento Confidencial Terceiro',
            f'CONF-{uuid4().hex[:6].upper()}',
            'Documento estritamente privado de terceiro.',
            stranger.id,
        ),
    ]

    for d_name, d_ident, d_desc, owner_id in docs_data:
        stmt = select(Document).where(
            Document.name == d_name, Document.deleted_at.is_(None)
        )
        if not await session.scalar(stmt):
            d = Document(
                name=d_name,
                identifier=d_ident,
                description=d_desc,
                processing_status='PROCESSED',
            )
            d.created_by = owner_id
            session.add(d)
            print(f'  ✓ Documento criado: {d_name}')
        else:
            print(f'  · Documento já existe: {d_name}')


async def seed_demo_data():
    """Popula o banco de dados com os perfis e entidades para a demo."""
    print('🌱 Iniciando seed dos dados de demonstração...')
    async with async_session() as session:
        users = await _seed_users(session)
        student = users['aluno_advisee@universidade.edu.br']
        advisor = users['advisor@universidade.edu.br']
        stranger = users['stranger@teste.com']

        await _seed_advisorship(session, advisor, student)
        await _seed_projects(session, student, advisor, stranger)
        await _seed_documents(session, student, advisor, stranger)

        await session.commit()
        print('✨ Seed concluído com sucesso!')


def main():
    asyncio.run(seed_demo_data())


if __name__ == '__main__':
    main()
