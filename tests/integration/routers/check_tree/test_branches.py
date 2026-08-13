from http import HTTPStatus

import pytest
import pytest_asyncio

from tests.factories.branch_factory import (
    BranchFactory,
    TaxonomyFactory,
    TypificationFactory,
)


@pytest_asyncio.fixture
async def setup_taxonomy(session, user):
    typ = TypificationFactory()
    typ.set_creation_audit(user.id)
    session.add(typ)
    await session.commit()

    tax = TaxonomyFactory(typification_id=typ.id)
    tax.set_creation_audit(user.id)
    session.add(tax)
    await session.commit()
    return tax


@pytest.mark.asyncio
async def test_create_branch_api(client, token, setup_taxonomy):
    response = client.post(
        '/branch',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'title': 'API Branch',
            'description': 'API Description',
            'taxonomy_id': str(setup_taxonomy.id),
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['title'] == 'API Branch'
    assert 'id' in data


@pytest.mark.asyncio
async def test_get_branches_api(client, token, session, user, setup_taxonomy):
    branch = BranchFactory(
        title='List API Branch', taxonomy_id=setup_taxonomy.id
    )
    branch.set_creation_audit(user.id)
    session.add(branch)
    await session.commit()

    response = client.get(
        '/branch', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert 'branches' in data
    titles = [b['title'] for b in data['branches']]
    assert 'List API Branch' in titles


@pytest.mark.asyncio
async def test_get_branch_by_id_api(
    client, token, session, user, setup_taxonomy
):
    branch = BranchFactory(
        title='Get By ID API', taxonomy_id=setup_taxonomy.id
    )
    branch.set_creation_audit(user.id)
    session.add(branch)
    await session.commit()

    response = client.get(
        f'/branch/{branch.id}', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['title'] == 'Get By ID API'


@pytest.mark.asyncio
async def test_update_branch_api(client, token, session, user, setup_taxonomy):
    branch = BranchFactory(title='Update Me', taxonomy_id=setup_taxonomy.id)
    branch.set_creation_audit(user.id)
    session.add(branch)
    await session.commit()

    response = client.put(
        '/branch',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'id': str(branch.id),
            'title': 'Updated API Branch',
            'description': 'Updated Description',
            'taxonomy_id': str(setup_taxonomy.id),
        },
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['title'] == 'Updated API Branch'


@pytest.mark.asyncio
async def test_delete_branch_api(client, token, session, user, setup_taxonomy):
    branch = BranchFactory(title='Delete Me', taxonomy_id=setup_taxonomy.id)
    branch.set_creation_audit(user.id)
    session.add(branch)
    await session.commit()

    response = client.delete(
        f'/branch/{branch.id}', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.NO_CONTENT
