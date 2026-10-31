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


def _create(client, token, taxonomy_id, **marking):
    return client.post(
        '/branch',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'title': 'Metodologia descrita',
            'description': 'O documento descreve a metodologia.',
            'taxonomy_id': str(taxonomy_id),
            **marking,
        },
    )


def _update(client, token, branch, **fields):
    return client.put(
        '/branch',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'id': branch['id'],
            'title': branch['title'],
            'description': branch['description'],
            'taxonomy_id': branch['taxonomy_id'],
            **fields,
        },
    )


def _marking(branch: dict) -> tuple:
    return branch['section_scope'], branch['expected_section']


@pytest.mark.asyncio
async def test_configurador_marca_secao_do_ramo_e_edicao_preserva_marcacao(
    client, token, setup_taxonomy
):
    headers = {'Authorization': f'Bearer {token}'}

    # 1. Cria o ramo marcado com a seção "Metodologia"
    response = _create(
        client,
        token,
        setup_taxonomy.id,
        section_scope='SPECIFIC_SECTION',
        expected_section='Metodologia',
    )
    assert response.status_code == HTTPStatus.CREATED
    branch = response.json()
    assert _marking(branch) == ('SPECIFIC_SECTION', 'Metodologia')

    # 2. Consulta o ramo e vê a mesma marcação
    response = client.get(f'/branch/{branch["id"]}', headers=headers)
    assert _marking(response.json()) == ('SPECIFIC_SECTION', 'Metodologia')

    # 3. Edita só o título, como o front-end atual faz
    response = _update(client, token, {**branch, 'title': 'Metodologia'})
    assert response.status_code == HTTPStatus.OK
    branch = response.json()
    assert branch['title'] == 'Metodologia'
    assert _marking(branch) == ('SPECIFIC_SECTION', 'Metodologia')

    # 4. Marca o ramo como documento inteiro
    response = _update(
        client, token, branch, section_scope='ENTIRE_DOCUMENT'
    )
    assert response.status_code == HTTPStatus.OK
    branch = response.json()
    assert _marking(branch) == ('ENTIRE_DOCUMENT', None)

    # 5. Remove a marcação
    response = _update(client, token, branch, section_scope='UNKNOWN')
    assert response.status_code == HTTPStatus.OK
    assert _marking(response.json()) == ('UNKNOWN', None)


@pytest.mark.asyncio
async def test_configurador_cria_e_edita_ramo_sem_chamar_modelo(
    client, token, setup_taxonomy, mock_fast_model_for_tests
):
    headers = {'Authorization': f'Bearer {token}'}

    # 1. O configurador cria o ramo e o vê na resposta.
    created = client.post(
        '/branch',
        headers=headers,
        json={
            'title': 'Busca',
            'description': 'Estratégia de busca',
            'taxonomy_id': str(setup_taxonomy.id),
        },
    )
    assert created.status_code == HTTPStatus.CREATED
    assert created.json()['title'] == 'Busca'

    # 2. O configurador edita a descrição e vê o novo texto.
    updated = client.put(
        '/branch',
        headers=headers,
        json={
            'id': created.json()['id'],
            'title': 'Busca',
            'description': 'Bases e descritores da busca',
            'taxonomy_id': str(setup_taxonomy.id),
        },
    )
    assert updated.status_code == HTTPStatus.OK
    assert updated.json()['description'] == 'Bases e descritores da busca'

    # 3. Nada leria uma geração do modelo rápido, então ele fica de fora.
    mock_fast_model_for_tests.with_structured_output.assert_not_called()


@pytest.mark.asyncio
async def test_ramo_criado_sem_marcacao_fica_sem_escopo(
    client, token, setup_taxonomy
):
    response = _create(client, token, setup_taxonomy.id)

    assert response.status_code == HTTPStatus.CREATED
    assert _marking(response.json()) == ('UNKNOWN', None)


INVALID_MARKINGS = [
    pytest.param({'section_scope': 'SPECIFIC_SECTION'}, id='secao-sem-nome'),
    pytest.param(
        {'section_scope': 'SPECIFIC_SECTION', 'expected_section': '   '},
        id='secao-em-branco',
    ),
    pytest.param(
        {'section_scope': 'ENTIRE_DOCUMENT', 'expected_section': 'Métodos'},
        id='secao-com-documento-inteiro',
    ),
    pytest.param(
        {'section_scope': 'UNKNOWN', 'expected_section': 'Métodos'},
        id='secao-sem-marcacao',
    ),
    pytest.param({'section_scope': 'CAPITULO'}, id='escopo-invalido'),
]


@pytest.mark.asyncio
@pytest.mark.parametrize('marking', INVALID_MARKINGS)
async def test_criacao_recusa_marcacao_invalida(
    client, token, setup_taxonomy, marking
):
    response = _create(client, token, setup_taxonomy.id, **marking)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'marking',
    [
        *INVALID_MARKINGS,
        pytest.param({'expected_section': 'Métodos'}, id='secao-sem-escopo'),
    ],
)
async def test_edicao_recusa_marcacao_invalida_sem_alterar_o_ramo(
    client, token, setup_taxonomy, marking
):
    branch = _create(
        client,
        token,
        setup_taxonomy.id,
        section_scope='SPECIFIC_SECTION',
        expected_section='Metodologia',
    ).json()

    response = _update(client, token, branch, **marking)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    stored = client.get(
        f'/branch/{branch["id"]}',
        headers={'Authorization': f'Bearer {token}'},
    ).json()
    assert _marking(stored) == ('SPECIFIC_SECTION', 'Metodologia')
