from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from lumina.core.dependencies import CurrentUser, Session
from lumina.schemas.project import (
    ProjectCreate,
    ProjectFilter,
    ProjectList,
    ProjectPublic,
    ProjectUpdate,
)
from lumina.services import project_service

router = APIRouter(
    prefix='/project',
    tags=['projetos'],
)


@router.post(
    '',
    status_code=HTTPStatus.CREATED,
    response_model=ProjectPublic,
    summary='Criar projeto',
    description='Cria um novo projeto associado a um grupo de documento.',
)
async def create_project(
    project: ProjectCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await project_service.create_project(
        session, current_user.id, project
    )


@router.get(
    '',
    response_model=ProjectList,
    summary='Listar projetos',
    description='Retorna todos os projetos, com filtros opcionais por nome e grupo de documento.',
)
async def read_projects(
    session: Session,
    filters: Annotated[ProjectFilter, Depends()],
):
    projects = await project_service.get_projects(session, filters)
    return {'projects': projects}


@router.get(
    '/{project_id}',
    response_model=ProjectPublic,
    summary='Obter projeto por ID',
    description='Retorna um projeto específico pelo seu UUID.',
)
async def read_project(project_id: UUID, session: Session):
    return await project_service.get_project_by_id(session, project_id)


@router.put(
    '',
    response_model=ProjectPublic,
    summary='Atualizar projeto',
    description='Atualiza os dados de um projeto existente.',
)
async def update_project(
    project: ProjectUpdate,
    session: Session,
    current_user: CurrentUser,
):
    return await project_service.update_project(
        session, current_user.id, project
    )


@router.delete(
    '/{project_id}',
    status_code=HTTPStatus.NO_CONTENT,
    summary='Excluir projeto',
    description='Remove (soft-delete) um projeto. Documentos associados serão removidos em cascata.',
)
async def delete_project(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await project_service.delete_project(session, current_user.id, project_id)
    return {'message': 'Project deleted'}
