import pytest

from lumina.models import Project
from lumina.repositories import project_repo
from lumina.schemas.project import ProjectFilter


@pytest.mark.asyncio
async def test_add_and_get_project(session, user):
    project = Project(name='Integration Test Project', description='Test')
    project.set_creation_audit(user.id)

    project_repo.add_project(session, project)
    await session.commit()

    db_project = await project_repo.get_by_id(session, project.id)
    assert db_project is not None
    assert db_project.name == 'Integration Test Project'


@pytest.mark.asyncio
async def test_get_by_name(session, user):
    project = Project(name='Unique Name', description='Test')
    project.set_creation_audit(user.id)

    project_repo.add_project(session, project)
    await session.commit()

    db_project = await project_repo.get_by_name(session, 'Unique Name')
    assert db_project is not None
    assert db_project.id == project.id


@pytest.mark.asyncio
async def test_list_all(session, user):
    project1 = Project(name='List Project A')
    project1.set_creation_audit(user.id)
    project2 = Project(name='List Project B')
    project2.set_creation_audit(user.id)

    project_repo.add_project(session, project1)
    project_repo.add_project(session, project2)
    await session.commit()

    filters = ProjectFilter(q='List Project', offset=0, limit=10)
    projects = await project_repo.list_all(session, user, filters)

    assert len(projects) >= 2
    names = [p.name for p in projects]
    assert 'List Project A' in names
    assert 'List Project B' in names
