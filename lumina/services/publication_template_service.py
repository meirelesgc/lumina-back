from http import HTTPStatus
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.core.dependencies import TemplateStorage
from lumina.core.settings import Settings
from lumina.models import PublicationTemplate
from lumina.repositories import publication_template_repo
from lumina.schemas.publication_template import (
    PublicationTemplateFilter,
    PublicationTemplatePublic,
    PublicationTemplateUpdate,
)
from lumina.services import audit_service

SETTINGS = Settings()

TEMPLATE_NOT_FOUND_DETAIL = 'Template não encontrado.'
TEMPLATE_NAME_CONFLICT_DETAIL = 'Já existe um template com esse nome.'


async def create_template(
    session: AsyncSession,
    user_id: UUID,
    storage: TemplateStorage,
    name: str,
    file: UploadFile,
) -> PublicationTemplate:
    existing = await publication_template_repo.get_by_name(session, name)
    if existing:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=TEMPLATE_NAME_CONFLICT_DETAIL,
        )

    unique_filename = f'{uuid4()}_{file.filename}'
    await storage.save(file, unique_filename)
    file_path = f'template_conformity/uploads/{unique_filename}'

    db_template = PublicationTemplate(
        name=name,
        original_filename=file.filename,
        file_path=file_path,
    )
    db_template.set_creation_audit(user_id)

    publication_template_repo.add(session, db_template)
    await session.flush()

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='CREATE',
        table_name=PublicationTemplate.__tablename__,
        record_id=db_template.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(db_template)
    return db_template


async def get_templates(
    session: AsyncSession, filters: PublicationTemplateFilter
) -> list[PublicationTemplate]:
    return await publication_template_repo.list_all(session, filters)


async def get_template_by_id(
    session: AsyncSession, template_id: UUID
) -> PublicationTemplate:
    template = await publication_template_repo.get_by_id(session, template_id)
    if not template or template.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=TEMPLATE_NOT_FOUND_DETAIL,
        )
    return template


async def update_template(
    session: AsyncSession,
    user_id: UUID,
    storage: TemplateStorage,
    data: PublicationTemplateUpdate,
    file: UploadFile | None,
) -> PublicationTemplate:
    db_template = await get_template_by_id(session, data.id)

    old_data = PublicationTemplatePublic.model_validate(
        db_template
    ).model_dump(mode='json')

    if data.name is not None and data.name != db_template.name:
        conflict = await publication_template_repo.get_by_name(
            session, data.name, exclude_id=data.id
        )
        if conflict:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=TEMPLATE_NAME_CONFLICT_DETAIL,
            )
        db_template.name = data.name

    if file is not None:
        old_file_path = db_template.file_path
        unique_filename = f'{uuid4()}_{file.filename}'
        await storage.save(file, unique_filename)
        db_template.file_path = f'template_conformity/uploads/{unique_filename}'
        db_template.original_filename = file.filename

        if old_file_path:
            await storage.delete(old_file_path.split('/')[-1])

    new_data = PublicationTemplatePublic.model_validate(
        db_template
    ).model_dump(mode='json')
    db_template.set_update_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='UPDATE',
        table_name=PublicationTemplate.__tablename__,
        record_id=db_template.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()
    await session.refresh(db_template)
    return db_template


async def delete_template(
    session: AsyncSession, user_id: UUID, template_id: UUID
) -> None:
    db_template = await get_template_by_id(session, template_id)

    old_data = PublicationTemplatePublic.model_validate(
        db_template
    ).model_dump(mode='json')
    db_template.set_deletion_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='DELETE',
        table_name=PublicationTemplate.__tablename__,
        record_id=db_template.id,
        old_data=old_data,
    )

    await session.commit()


async def get_template_file_path(
    session: AsyncSession, template_id: UUID
) -> Path:
    # Usado pelo fluxo de conformidade (routers/templates.py) para obter o PDF de referência gravado em disco a partir do template cadastrado.
    template = await get_template_by_id(session, template_id)
    full_path = Path(SETTINGS.STORAGE_DIRECTORY) / template.file_path
    if not full_path.is_file():
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=TEMPLATE_NOT_FOUND_DETAIL,
        )
    return full_path
