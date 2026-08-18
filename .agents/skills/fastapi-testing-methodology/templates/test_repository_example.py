"""
Template: Teste de Integração (Repository)

Foco: Funcionalidade de consultas no Banco de Dados.
Usa a `session` real injetada pelo conftest.
"""

import pytest

from lumina.models import Project
from lumina.repositories import project_repo
from lumina.schemas.project import ProjectFilter


@pytest.mark.asyncio
async def test_repository_list_and_get_by_name(session, user):
    """
    Testa se uma consulta de repositório filtra e retorna os dados corretos.
    """
    # Arrange: Popula banco vinculando à auditoria do usuário
    project = Project(name='Projeto Integracao', description='Descricao')
    project.set_creation_audit(user.id)
    project_repo.add_project(session, project)
    await session.commit()

    # Act
    filters = ProjectFilter(q='Integracao', offset=0, limit=10)
    results = await project_repo.list_all(session, filters)
    found_project = await project_repo.get_by_name(
        session, 'Projeto Integracao'
    )

    # Assert
    assert len(results) >= 1
    assert any(p.name == 'Projeto Integracao' for p in results)
    assert found_project is not None
    assert found_project.id == project.id
