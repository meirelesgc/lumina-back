from http import HTTPStatus
from typing import Optional, Sequence
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.models import AccessType, Advisorship, Document, User
from lumina.repositories import (
    advisorship_repo,
    doc_repo,
    project_repo,
    user_repo,
)
from lumina.schemas.advisorship import (
    AdviseeCardPublic,
    AdvisorCardPublic,
    AdvisorshipCreate,
    AdvisorshipFilter,
    AdvisorshipPublic,
    AdvisorshipUpdate,
    DocumentAcademicContextPublic,
)
from lumina.schemas.project import ProjectPublic
from lumina.schemas.user import UserPublic
from lumina.services import audit_service


async def create_advisorship(
    session: AsyncSession, current_user: User, data: AdvisorshipCreate
) -> Advisorship:
    if data.advisor_id == data.advisee_id:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Um usuário não pode ser orientador de si mesmo.',
        )

    advisor = await user_repo.get_by_id(session, data.advisor_id)
    if not advisor or advisor.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Orientador não encontrado.',
        )

    advisee = await user_repo.get_by_id(session, data.advisee_id)
    if not advisee or advisee.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Orientando não encontrado.',
        )

    if data.project_id:
        project = await project_repo.get_by_id(session, data.project_id)
        if not project or project.deleted_at:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Projeto não encontrado.',
            )

    existing = await advisorship_repo.get_active_pair(
        session=session,
        advisor_id=data.advisor_id,
        advisee_id=data.advisee_id,
        project_id=data.project_id,
        role_type=data.role_type.value,
    )
    if existing:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Já existe um vínculo ativo com esses dados.',
        )

    db_advisorship = Advisorship(
        advisor_id=data.advisor_id,
        advisee_id=data.advisee_id,
        project_id=data.project_id,
        role_type=data.role_type.value,
        topic=data.topic,
        status='ACTIVE',
    )
    db_advisorship.set_creation_audit(current_user.id)
    advisorship_repo.add_advisorship(session, db_advisorship)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='CREATE',
        table_name=Advisorship.__tablename__,
        record_id=db_advisorship.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(db_advisorship)
    return db_advisorship


async def get_advisorship_by_id(
    session: AsyncSession, current_user: User, advisorship_id: UUID
) -> Advisorship:
    advisorship = await advisorship_repo.get_by_id(session, advisorship_id)
    if not advisorship or advisorship.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Vínculo de orientação não encontrado.',
        )

    is_admin = current_user.access_level == AccessType.ADMIN
    is_party = current_user.id in {
        advisorship.advisor_id,
        advisorship.advisee_id,
    }

    if not is_admin and not is_party:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Acesso negado a este vínculo de orientação.',
        )

    return advisorship


async def update_advisorship(
    session: AsyncSession,
    current_user: User,
    advisorship_id: UUID,
    data: AdvisorshipUpdate,
) -> Advisorship:
    advisorship = await advisorship_repo.get_by_id(session, advisorship_id)
    if not advisorship or advisorship.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Vínculo de orientação não encontrado.',
        )

    is_admin = current_user.access_level == AccessType.ADMIN
    is_advisor = advisorship.advisor_id == current_user.id

    if not is_admin and not is_advisor:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Apenas orientador ou admin podem atualizar.',
        )

    old_data = AdvisorshipPublic.model_validate(advisorship).model_dump(
        mode='json'
    )

    if data.project_id is not None:
        if data.project_id:
            project = await project_repo.get_by_id(session, data.project_id)
            if not project or project.deleted_at:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail='Projeto não encontrado.',
                )
        advisorship.project_id = data.project_id

    if data.role_type is not None:
        advisorship.role_type = data.role_type.value

    if data.topic is not None:
        advisorship.topic = data.topic

    if data.status is not None:
        advisorship.status = data.status.value

    new_data = AdvisorshipPublic.model_validate(advisorship).model_dump(
        mode='json'
    )
    advisorship.set_update_audit(current_user.id)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=Advisorship.__tablename__,
        record_id=advisorship.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()
    await session.refresh(advisorship)
    return advisorship


async def delete_advisorship(
    session: AsyncSession, current_user: User, advisorship_id: UUID
) -> None:
    advisorship = await advisorship_repo.get_by_id(session, advisorship_id)
    if not advisorship or advisorship.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Vínculo de orientação não encontrado.',
        )

    is_admin = current_user.access_level == AccessType.ADMIN
    is_advisor = advisorship.advisor_id == current_user.id

    if not is_admin and not is_advisor:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Apenas orientador ou admin podem remover.',
        )

    old_data = AdvisorshipPublic.model_validate(advisorship).model_dump(
        mode='json'
    )
    advisorship.set_deletion_audit(current_user.id)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='DELETE',
        table_name=Advisorship.__tablename__,
        record_id=advisorship.id,
        old_data=old_data,
    )

    await session.commit()


async def list_advisorships(
    session: AsyncSession, current_user: User, filters: AdvisorshipFilter
) -> Sequence[Advisorship]:
    is_admin = current_user.access_level == AccessType.ADMIN
    if not is_admin:
        if not filters.advisor_id and not filters.advisee_id:
            filters.advisor_id = current_user.id
        elif current_user.id not in {filters.advisor_id, filters.advisee_id}:
            filters.advisor_id = current_user.id

    return await advisorship_repo.list_all(session, filters)


async def get_my_advisees(
    session: AsyncSession,
    current_user: User,
    status: Optional[str] = None,
) -> list[AdviseeCardPublic]:
    relationships = await advisorship_repo.list_by_advisor(
        session, current_user.id, status=status
    )
    advisee_cards: list[AdviseeCardPublic] = []

    for rel in relationships:
        metrics = await advisorship_repo.get_advisee_document_metrics(
            session, rel.advisee_id, rel.project_id
        )
        advisee_cards.append(
            AdviseeCardPublic(
                advisee=UserPublic.model_validate(rel.advisee),
                advisorship_id=rel.id,
                role_type=rel.role_type,
                topic=rel.topic,
                status=rel.status,
                project=(
                    ProjectPublic.model_validate(rel.project)
                    if rel.project
                    else None
                ),
                total_documents=metrics['total'],
                pending_reviews=metrics['pending'],
            )
        )

    return advisee_cards


async def get_my_advisors(
    session: AsyncSession,
    current_user: User,
    status: Optional[str] = None,
) -> list[AdvisorCardPublic]:
    relationships = await advisorship_repo.list_by_advisee(
        session, current_user.id, status=status
    )
    return [
        AdvisorCardPublic(
            advisor=UserPublic.model_validate(rel.advisor),
            advisorship_id=rel.id,
            role_type=rel.role_type,
            topic=rel.topic,
            status=rel.status,
            project=(
                ProjectPublic.model_validate(rel.project)
                if rel.project
                else None
            ),
        )
        for rel in relationships
    ]


async def get_advisee_documents(
    session: AsyncSession,
    current_user: User,
    advisee_id: UUID,
    project_id: Optional[UUID] = None,
) -> list[Document]:
    is_admin = current_user.access_level == AccessType.ADMIN
    is_self = current_user.id == advisee_id

    if not is_admin and not is_self:
        active_pair = await advisorship_repo.get_active_pair(
            session=session,
            advisor_id=current_user.id,
            advisee_id=advisee_id,
            project_id=project_id,
        )
        if not active_pair:
            # Verifica se é orientador em qualquer projeto deste aluno
            all_rels = await advisorship_repo.list_by_advisor(
                session, current_user.id
            )
            has_rel = any(r.advisee_id == advisee_id for r in all_rels)
            if not has_rel:
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail='Sem permissão para ver documentos deste aluno.',
                )

    docs = await advisorship_repo.get_advisee_documents(
        session, advisee_id, project_id
    )
    return list(docs)


async def get_document_academic_context(
    session: AsyncSession, current_user: User, doc_id: UUID
) -> DocumentAcademicContextPublic:
    doc = await doc_repo.get_by_id(session, doc_id)
    if not doc or doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Documento não encontrado.',
        )

    author = None
    if doc.created_by:
        author = await user_repo.get_by_id(session, doc.created_by)

    advisors: list[User] = []
    advisorship_data = None
    project_data = None

    if doc.advisorship_id:
        adv = await advisorship_repo.get_by_id(session, doc.advisorship_id)
        if adv and not adv.deleted_at:
            advisorship_data = AdvisorshipPublic.model_validate(adv)
            if adv.advisor and adv.advisor not in advisors:
                advisors.append(adv.advisor)
            if adv.project:
                project_data = ProjectPublic.model_validate(adv.project)

    if doc.project_document_id and not project_data:
        project_doc = doc.project_document
        if project_doc and project_doc.project:
            project_data = ProjectPublic.model_validate(project_doc.project)
            # Busca orientadores vinculados a este projeto
            rels = await advisorship_repo.list_all(
                session,
                AdvisorshipFilter(project_id=project_doc.project_id, limit=50),
            )
            for r in rels:
                if r.advisor and r.advisor not in advisors:
                    advisors.append(r.advisor)

    return DocumentAcademicContextPublic(
        document_id=doc.id,
        document_name=doc.name,
        author=UserPublic.model_validate(author) if author else None,
        advisors=[UserPublic.model_validate(a) for a in advisors],
        project=project_data,
        advisorship=advisorship_data,
    )
