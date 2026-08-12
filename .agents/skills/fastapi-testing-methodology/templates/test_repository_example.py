"""
Template: Teste de Integração (Repository)

Foco: Funcionalidade de consultas complexas no Banco de Dados.
Usa a `session` real injetada pelo conftest.
"""
import pytest

# from lumina.repositories.project_repo import ProjectRepository

@pytest.mark.asyncio
async def test_repository_complex_query(session, project_factory, user_factory):
    """
    Testa se uma consulta com JOIN e GROUP BY traz os dados corretos.
    """
    # Arrange: Popula banco usando Factories
    # owner = await user_factory.create(session)
    # project_1 = await project_factory.create(session, owner=owner, name="Proj A")
    # project_2 = await project_factory.create(session, owner=owner, name="Proj B")
    
    # repo = ProjectRepository(session)
    
    # Act
    # results = await repo.get_user_projects_summary(user_id=owner.id)
    
    # Assert
    # assert len(results) == 2
    # assert results[0].name == "Proj A"
    pass
