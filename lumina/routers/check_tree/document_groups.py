from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from lumina.core.dependencies import CurrentUser, Session
from lumina.schemas.document_group import (
    DocumentGroupCreate,
    DocumentGroupFilter,
    DocumentGroupItemCreate,
    DocumentGroupItemOrder,
    DocumentGroupItemPublic,
    DocumentGroupItemUpdate,
    DocumentGroupList,
    DocumentGroupPublic,
    DocumentGroupUpdate,
)
from lumina.schemas.study_attachment import (
    StudyAttachmentCreate,
    StudyAttachmentOrder,
    StudyAttachmentPublic,
    StudyAttachmentUpdate,
)
from lumina.services import document_group_service, study_attachment_service

router = APIRouter(
    prefix='/document-group',
    tags=['configurador, grupos de documentos'],
)


@router.post(
    '',
    status_code=HTTPStatus.CREATED,
    response_model=DocumentGroupPublic,
    summary='Criar grupo de documento',
    description='Cria um novo grupo de documento no configurador.',
)
async def create_group(
    group: DocumentGroupCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await document_group_service.create_group(
        session, current_user.id, group
    )


@router.get(
    '',
    response_model=DocumentGroupList,
    summary='Listar grupos de documento',
    description='Retorna todos os grupos de documento cadastrados, com filtro opcional por nome.',
)
async def read_groups(
    session: Session,
    filters: Annotated[DocumentGroupFilter, Depends()],
):
    groups = await document_group_service.get_groups(session, filters)
    return {'groups': groups}


@router.get(
    '/{group_id}',
    response_model=DocumentGroupPublic,
    summary='Obter grupo de documento por ID',
    description='Retorna um grupo de documento específico pelo seu UUID.',
)
async def read_group(group_id: UUID, session: Session):
    return await document_group_service.get_group_by_id(session, group_id)


@router.put(
    '',
    response_model=DocumentGroupPublic,
    summary='Atualizar grupo de documento',
    description='Atualiza os dados de um grupo de documento existente.',
)
async def update_group(
    group: DocumentGroupUpdate,
    session: Session,
    current_user: CurrentUser,
):
    return await document_group_service.update_group(
        session, current_user.id, group
    )


@router.delete(
    '/{group_id}',
    status_code=HTTPStatus.NO_CONTENT,
    summary='Excluir grupo de documento',
    description='Remove (soft-delete) um grupo de documento. Itens associados serão removidos em cascata.',
)
async def delete_group(
    group_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await document_group_service.delete_group(
        session, current_user.id, group_id
    )
    return {'message': 'Document group deleted'}


@router.post(
    '/{group_id}/item',
    status_code=HTTPStatus.CREATED,
    response_model=DocumentGroupItemPublic,
    summary='Criar item de grupo',
    description='Adiciona um novo item a um grupo de documento existente.',
)
async def create_item(
    group_id: UUID,
    item: DocumentGroupItemCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await document_group_service.create_item(
        session, current_user.id, group_id, item
    )


@router.get(
    '/{group_id}/items',
    response_model=list[DocumentGroupItemPublic],
    summary='Listar itens de um grupo',
    description='Retorna todos os itens pertencentes a um grupo de documento específico.',
)
async def read_items_by_group(group_id: UUID, session: Session):
    from lumina.repositories import document_group_repo

    return await document_group_repo.get_items_by_group(session, group_id)


@router.put(
    '/{group_id}/items/order',
    response_model=DocumentGroupPublic,
    summary='Reordenar itens de um grupo',
    description='Recebe a lista completa de ids dos itens ativos do grupo na ordem desejada e grava as posições 1, 2, 3...',
)
async def reorder_items(
    group_id: UUID,
    order: DocumentGroupItemOrder,
    session: Session,
    current_user: CurrentUser,
):
    return await document_group_service.reorder_items(
        session, current_user.id, group_id, order
    )


@router.put(
    '/item',
    response_model=DocumentGroupItemPublic,
    summary='Atualizar item de grupo',
    description='Atualiza o nome de um item de grupo de documento.',
)
async def update_item(
    item: DocumentGroupItemUpdate,
    session: Session,
    current_user: CurrentUser,
):
    return await document_group_service.update_item(
        session, current_user.id, item
    )


@router.delete(
    '/item/{item_id}',
    status_code=HTTPStatus.NO_CONTENT,
    summary='Excluir item de grupo',
    description='Remove (soft-delete) um item de grupo de documento.',
)
async def delete_item(
    item_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await document_group_service.delete_item(session, current_user.id, item_id)
    return {'message': 'Document group item deleted'}


@router.post(
    '/item/{item_id}/attachment',
    status_code=HTTPStatus.CREATED,
    response_model=StudyAttachmentPublic,
    summary='Criar anexo de estudo',
    description='Anexa uma tipificação, um artigo por DOI ou um link ao fim da lista de estudo de um item de grupo.',
)
async def create_attachment(
    item_id: UUID,
    attachment: StudyAttachmentCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await study_attachment_service.create_attachment(
        session, current_user.id, item_id, attachment
    )


@router.get(
    '/item/{item_id}/attachments',
    response_model=list[StudyAttachmentPublic],
    summary='Listar anexos de estudo de um item',
    description='Retorna os anexos ativos do item, na ordem de estudo.',
)
async def read_attachments(item_id: UUID, session: Session):
    return await study_attachment_service.list_attachments(session, item_id)


@router.put(
    '/item/{item_id}/attachments/order',
    response_model=list[StudyAttachmentPublic],
    summary='Reordenar anexos de estudo',
    description='Recebe a lista completa de ids dos anexos do item na ordem desejada.',
)
async def reorder_attachments(
    item_id: UUID,
    order: StudyAttachmentOrder,
    session: Session,
    current_user: CurrentUser,
):
    return await study_attachment_service.reorder_attachments(
        session, current_user.id, item_id, order
    )


@router.put(
    '/attachment',
    response_model=StudyAttachmentPublic,
    summary='Atualizar anexo de estudo',
    description='Atualiza um anexo de estudo. O tipo do anexo não muda.',
)
async def update_attachment(
    attachment: StudyAttachmentUpdate,
    session: Session,
    current_user: CurrentUser,
):
    return await study_attachment_service.update_attachment(
        session, current_user.id, attachment
    )


@router.delete(
    '/attachment/{attachment_id}',
    status_code=HTTPStatus.NO_CONTENT,
    summary='Excluir anexo de estudo',
    description='Remove (soft-delete) um anexo de estudo.',
)
async def delete_attachment(
    attachment_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await study_attachment_service.delete_attachment(
        session, current_user.id, attachment_id
    )
