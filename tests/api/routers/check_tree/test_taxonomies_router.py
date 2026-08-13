from http import HTTPStatus

import pytest
import pytest_asyncio

from lumina.models import Taxonomy, Typification


@pytest_asyncio.fixture
async def typification(session):
    typ = Typification(name='Router Typification')
    session.add(typ)
    await session.commit()
    await session.refresh(typ)
    return typ


@pytest.mark.asyncio
async def test_create_taxonomy_router(client, token, typification):
    response = client.post(
        '/taxonomy',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'title': 'New Taxonomy',
            'description': 'Description',
            'typification_id': str(typification.id),
            'source_ids': [],
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['title'] == 'New Taxonomy'
    assert 'id' in data


@pytest.mark.asyncio
async def test_read_taxonomies_router(client, token, session, typification):
    tax = Taxonomy(
        title='Existing Taxonomy',
        description='',
        typification_id=typification.id,
    )
    session.add(tax)
    await session.commit()

    response = client.get(
        '/taxonomy', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert 'taxonomies' in data
    assert len(data['taxonomies']) > 0


@pytest.mark.asyncio
async def test_read_taxonomy_by_id_router(
    client, token, session, typification
):
    tax = Taxonomy(
        title='Get Taxonomy', description='', typification_id=typification.id
    )
    session.add(tax)
    await session.commit()
    await session.refresh(tax)

    response = client.get(
        f'/taxonomy/{tax.id}', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(tax.id)
    assert data['title'] == 'Get Taxonomy'


@pytest.mark.asyncio
async def test_delete_taxonomy_router(client, token, session, typification):
    tax = Taxonomy(
        title='Delete Taxonomy',
        description='',
        typification_id=typification.id,
    )
    session.add(tax)
    await session.commit()
    await session.refresh(tax)

    response = client.delete(
        f'/taxonomy/{tax.id}', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.NO_CONTENT
