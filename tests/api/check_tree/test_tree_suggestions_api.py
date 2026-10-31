import contextlib
from functools import partial
from http import HTTPStatus
from uuid import uuid4

import pytest

from lumina.app import app
from lumina.core.storage_provider import get_storage_provider
from lumina.services import tree_suggestion_service as service
from lumina.services.ai.tree_suggestion import generate_tree_suggestions
from tests.factories.tree_suggestion_factory import (
    ESTRUTURA,
    INTRODUCAO,
    TCC,
    FakeStructuredModel,
    build_normative_pdf,
    default_create_responses,
)

pytestmark = pytest.mark.usefixtures('user_is_admin')


class FakeStorage:
    def __init__(self):
        self.saved = []

    async def save(self, file, filename):
        self.saved.append(filename)
        return f'/uploads/{filename}'


@pytest.fixture
def pdf_path(tmp_path):
    return build_normative_pdf(tmp_path / 'regulamento.pdf')


@pytest.fixture
def api(client, session, monkeypatch, pdf_path):
    """Cliente com storage fake e geração em background com modelo fake."""

    @contextlib.asynccontextmanager
    async def test_session():
        yield session

    model = FakeStructuredModel(default_create_responses())
    monkeypatch.setattr(service, 'async_session', test_session)
    monkeypatch.setattr(service, '_local_path', lambda _: str(pdf_path))
    monkeypatch.setattr(
        service,
        'generate_tree_suggestions',
        partial(generate_tree_suggestions, model=model, fast_model=model),
    )
    storage = FakeStorage()
    app.dependency_overrides[get_storage_provider] = lambda: storage
    yield client
    app.dependency_overrides.pop(get_storage_provider, None)


def _headers(token):
    return {'Authorization': f'Bearer {token}'}


def _upload(api, token, pdf_path, **data):
    return api.post(
        '/tree-suggestion',
        headers=_headers(token),
        files={
            'file': (
                'regulamento.pdf',
                pdf_path.read_bytes(),
                'application/pdf',
            )
        },
        data=data,
    )


def _item(detail, kind, title=None):
    return next(
        i
        for i in detail['items']
        if i['kind'] == kind
        and (title is None or i['proposed_title'] == title)
    )


def test_full_review_flow(api, token, pdf_path):
    response = _upload(api, token, pdf_path)
    assert response.status_code == HTTPStatus.ACCEPTED
    assert response.json()['status'] == 'processing'
    session_id = response.json()['id']

    detail = api.get(
        f'/tree-suggestion/{session_id}', headers=_headers(token)
    ).json()
    assert detail['status'] == 'ready'
    assert detail['excluded_rules'][0] == {
        'title': 'Fonte Arial 12',
        'quote': 'O texto deve ser digitado em fonte Arial tamanho 12.',
        'pages': [2],
    }
    assert _item(detail, 'branch', INTRODUCAO)['evidence'][0]['pages'] == [4]

    listed = api.get(
        '/tree-suggestion', params={'status': 'ready'}, headers=_headers(token)
    ).json()
    assert session_id in {s['id'] for s in listed['sessions']}

    base = f'/tree-suggestion/{session_id}/items'
    typ = _item(detail, 'typification', TCC)
    response = api.post(
        f'{base}/{typ["id"]}/confirm',
        headers=_headers(token),
        json={'title': 'TCC'},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['final_title'] == 'TCC'

    taxonomy = _item(detail, 'taxonomy', ESTRUTURA)
    branch = _item(detail, 'branch', INTRODUCAO)
    assert (
        api.post(
            f'{base}/{taxonomy["id"]}/confirm', headers=_headers(token)
        ).status_code
        == HTTPStatus.OK
    )
    assert (
        api.post(
            f'{base}/{branch["id"]}/confirm', headers=_headers(token)
        ).status_code
        == HTTPStatus.OK
    )

    response = api.post(
        f'{base}/{_item(detail, "source")["id"]}/discard',
        headers=_headers(token),
    )
    assert response.status_code == HTTPStatus.OK
    assert _item(response.json(), 'source')['status'] == 'discarded'

    response = api.post(
        f'/tree-suggestion/{session_id}/discard', headers=_headers(token)
    )
    final = response.json()
    assert final['status'] == 'completed'
    assert {i['status'] for i in final['items']} == {'confirmed', 'discarded'}

    response = api.post(
        f'{base}/{branch["id"]}/confirm', headers=_headers(token)
    )
    assert response.status_code == HTTPStatus.CONFLICT


def test_enrich_mode_exposes_target_name(api, token, pdf_path):
    typification = api.post(
        '/typification',
        headers=_headers(token),
        json={'name': TCC, 'source_ids': []},
    ).json()

    response = _upload(
        api, token, pdf_path, typification_id=typification['id']
    )

    assert response.status_code == HTTPStatus.ACCEPTED
    assert response.json()['mode'] == 'enrich'
    detail = api.get(
        f'/tree-suggestion/{response.json()["id"]}', headers=_headers(token)
    ).json()
    assert detail['target_typification_name'] == TCC


def test_upload_rejects_non_pdf(api, token):
    response = api.post(
        '/tree-suggestion',
        headers=_headers(token),
        files={'file': ('nota.txt', b'texto', 'text/plain')},
    )
    assert response.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE


def test_unknown_session_returns_404(api, token):
    response = api.get(f'/tree-suggestion/{uuid4()}', headers=_headers(token))
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_requires_authentication(client):
    assert client.get('/tree-suggestion').status_code == (
        HTTPStatus.UNAUTHORIZED
    )
    assert client.post(f'/tree-suggestion/{uuid4()}/discard').status_code == (
        HTTPStatus.UNAUTHORIZED
    )
