from http import HTTPStatus
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from lumina.core.settings import Settings
from lumina.features import template_conformity_service

PDF_BYTES = b'%PDF-1.4 dummy template'
STORAGE_DIR = Path(Settings().STORAGE_DIRECTORY)


def _auth(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def _pdf_files(filename: str = 'revista.pdf') -> dict:
    return {'file': (filename, PDF_BYTES, 'application/pdf')}


def _unlink_stored(file_path: str) -> None:
    path = STORAGE_DIR / file_path
    if path.is_file():
        path.unlink()


def _create_template(client, token, name: str | None = None):
    payload_name = name or f'Template {uuid4()}'
    response = client.post(
        '/templates',
        headers=_auth(token),
        data={'name': payload_name},
        files=_pdf_files(),
    )
    assert response.status_code == HTTPStatus.CREATED
    return response.json()


@pytest.fixture(autouse=True)
def isolate_template_store(tmp_path, monkeypatch):
    uploads = tmp_path / 'uploads'
    uploads.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        template_conformity_service, 'UPLOADS_DIR', uploads
    )


@pytest.fixture(autouse=True)
def mock_template_compare(mocker):
    report = MagicMock()
    report.model_dump.return_value = {
        'metadata': {
            'approach': 'hybrid',
            'model': 'test',
            'template_file': 'template.pdf',
            'article_file': 'artigo.pdf',
        },
        'summary': {
            'is_compliant': True,
            'sections_total': 0,
            'sections_passed': 0,
            'description': 'ok',
        },
        'sections': [],
    }
    mocker.patch(
        'lumina.features.template_conformity_service.template_check.compare',
        new_callable=AsyncMock,
        return_value=report,
    )


def test_list_templates_unauthorized(client):
    response = client.get('/templates')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_create_template_unauthorized(client):
    response = client.post(
        '/templates',
        data={'name': 'Sem auth'},
        files=_pdf_files(),
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_template_unauthorized(client):
    response = client.get(f'/templates/{uuid4()}')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_update_template_unauthorized(client):
    response = client.put(
        f'/templates/{uuid4()}',
        data={'name': 'Novo nome'},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_delete_template_unauthorized(client):
    response = client.delete(f'/templates/{uuid4()}')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_process_template_compliance_unauthorized(client):
    response = client.post(
        f'/templates/{uuid4()}/conformidade',
        data={'template_id': str(uuid4())},
        files=_pdf_files('artigo.pdf'),
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_template_compliance_unauthorized(client):
    response = client.get(f'/templates/{uuid4()}/conformidade')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_list_template_compliance_unauthorized(client):
    response = client.get('/templates/results')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_template_compliance_by_id_unauthorized(client):
    response = client.get(f'/templates/results/{uuid4()}')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_delete_template_compliance_unauthorized(client):
    response = client.delete(f'/templates/results/{uuid4()}')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_list_templates_empty(client, token):
    response = client.get('/templates', headers=_auth(token))
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'templates': []}


def test_create_template(client, token):
    name = f'Template {uuid4()}'
    response = client.post(
        '/templates',
        headers=_auth(token),
        data={'name': name},
        files=_pdf_files('capa.pdf'),
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['name'] == name
    assert data['original_filename'] == 'capa.pdf'
    assert data['file_path'].startswith('template_conformity/uploads/')
    assert 'id' in data
    _unlink_stored(data['file_path'])


def test_create_template_conflict(client, token):
    created = _create_template(client, token, name='Template duplicado')
    response = client.post(
        '/templates',
        headers=_auth(token),
        data={'name': 'Template duplicado'},
        files=_pdf_files(),
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {
        'detail': 'Já existe um template com esse nome.'
    }
    _unlink_stored(created['file_path'])


def test_create_template_missing_file(client, token):
    response = client.post(
        '/templates',
        headers=_auth(token),
        data={'name': f'Template {uuid4()}'},
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_get_template_by_id(client, token):
    created = _create_template(client, token)
    response = client.get(
        f'/templates/{created["id"]}', headers=_auth(token)
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == created['id']
    assert data['name'] == created['name']
    _unlink_stored(created['file_path'])


def test_get_template_not_found(client, token):
    response = client.get(f'/templates/{uuid4()}', headers=_auth(token))
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Template não encontrado.'}


def test_list_templates_with_item(client, token):
    created = _create_template(client, token)
    response = client.get('/templates', headers=_auth(token))

    assert response.status_code == HTTPStatus.OK
    templates = response.json()['templates']
    assert any(item['id'] == created['id'] for item in templates)
    _unlink_stored(created['file_path'])


def test_list_templates_filter_by_name(client, token):
    unique = f'RevistaX{uuid4().hex[:8]}'
    created = _create_template(client, token, name=unique)
    other = _create_template(client, token, name=f'Outro {uuid4()}')

    response = client.get(
        '/templates',
        headers=_auth(token),
        params={'q': unique},
    )

    assert response.status_code == HTTPStatus.OK
    templates = response.json()['templates']
    assert len(templates) == 1
    assert templates[0]['id'] == created['id']
    _unlink_stored(created['file_path'])
    _unlink_stored(other['file_path'])


def test_update_template_name(client, token):
    created = _create_template(client, token)
    new_name = f'Template atualizado {uuid4()}'
    response = client.put(
        f'/templates/{created["id"]}',
        headers=_auth(token),
        data={'name': new_name},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['name'] == new_name
    assert data['id'] == created['id']
    _unlink_stored(created['file_path'])


def test_update_template_file(client, token):
    created = _create_template(client, token)
    response = client.put(
        f'/templates/{created["id"]}',
        headers=_auth(token),
        files=_pdf_files('novo.pdf'),
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['original_filename'] == 'novo.pdf'
    assert data['file_path'] != created['file_path']
    assert data['file_path'].startswith('template_conformity/uploads/')
    _unlink_stored(data['file_path'])


def test_update_template_not_found(client, token):
    response = client.put(
        f'/templates/{uuid4()}',
        headers=_auth(token),
        data={'name': 'Inexistente'},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_update_template_name_conflict(client, token):
    first = _create_template(client, token, name='Nome A')
    second = _create_template(client, token, name='Nome B')
    response = client.put(
        f'/templates/{second["id"]}',
        headers=_auth(token),
        data={'name': 'Nome A'},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {
        'detail': 'Já existe um template com esse nome.'
    }
    _unlink_stored(first['file_path'])
    _unlink_stored(second['file_path'])


def test_delete_template(client, token):
    created = _create_template(client, token)
    response = client.delete(
        f'/templates/{created["id"]}', headers=_auth(token)
    )
    assert response.status_code == HTTPStatus.NO_CONTENT

    check = client.get(
        f'/templates/{created["id"]}', headers=_auth(token)
    )
    assert check.status_code == HTTPStatus.NOT_FOUND
    _unlink_stored(created['file_path'])


def test_delete_template_not_found(client, token):
    response = client.delete(
        f'/templates/{uuid4()}', headers=_auth(token)
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_template_compliance_empty(client, token):
    doc_id = str(uuid4())
    response = client.get(
        f'/templates/{doc_id}/conformidade', headers=_auth(token)
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'count': 0, 'results': []}


def test_process_template_compliance(client, token):
    template = _create_template(client, token)
    doc_id = str(uuid4())
    response = client.post(
        f'/templates/{doc_id}/conformidade',
        headers=_auth(token),
        data={'template_id': template['id']},
        files=_pdf_files('artigo.pdf'),
    )

    assert response.status_code == HTTPStatus.ACCEPTED
    data = response.json()
    assert data['doc_id'] == doc_id
    assert data['status'] == 'processing'
    assert data['file_path'].startswith('template_conformity/uploads/')
    assert 'id' in data
    assert 'created_at' in data
    _unlink_stored(template['file_path'])


def test_process_template_compliance_template_not_found(client, token):
    response = client.post(
        f'/templates/{uuid4()}/conformidade',
        headers=_auth(token),
        data={'template_id': str(uuid4())},
        files=_pdf_files('artigo.pdf'),
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Template não encontrado.'}


def test_process_template_compliance_missing_file(client, token):
    template = _create_template(client, token)
    response = client.post(
        f'/templates/{uuid4()}/conformidade',
        headers=_auth(token),
        data={'template_id': template['id']},
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    _unlink_stored(template['file_path'])


def test_get_template_compliance_after_process(client, token):
    template = _create_template(client, token)
    doc_id = str(uuid4())
    accepted = client.post(
        f'/templates/{doc_id}/conformidade',
        headers=_auth(token),
        data={'template_id': template['id']},
        files=_pdf_files('artigo.pdf'),
    )
    assert accepted.status_code == HTTPStatus.ACCEPTED

    response = client.get(
        f'/templates/{doc_id}/conformidade', headers=_auth(token)
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body['count'] == 1
    result = body['results'][0]
    assert result['id'] == accepted.json()['id']
    assert result['doc_id'] == doc_id
    assert result['status'] == 'completed'
    assert result['report']['summary']['is_compliant'] is True
    _unlink_stored(template['file_path'])


def test_get_template_compliance_newest_first(client, token):
    template = _create_template(client, token)
    doc_id = str(uuid4())
    first = client.post(
        f'/templates/{doc_id}/conformidade',
        headers=_auth(token),
        data={'template_id': template['id']},
        files=_pdf_files('artigo1.pdf'),
    )
    second = client.post(
        f'/templates/{doc_id}/conformidade',
        headers=_auth(token),
        data={'template_id': template['id']},
        files=_pdf_files('artigo2.pdf'),
    )

    response = client.get(
        f'/templates/{doc_id}/conformidade', headers=_auth(token)
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    expected_ids = [second.json()['id'], first.json()['id']]
    assert body['count'] == len(expected_ids)
    ids = [item['id'] for item in body['results']]
    assert ids == expected_ids
    _unlink_stored(template['file_path'])


def test_list_template_compliance_global_and_filters(client, token):
    template = _create_template(client, token)
    doc_id1 = str(uuid4())
    doc_id2 = str(uuid4())

    res1 = client.post(
        f'/templates/{doc_id1}/conformidade',
        headers=_auth(token),
        data={'template_id': template['id']},
        files=_pdf_files('artigo1.pdf'),
    )
    res2 = client.post(
        f'/templates/{doc_id2}/conformidade',
        headers=_auth(token),
        data={'template_id': template['id']},
        files=_pdf_files('artigo2.pdf'),
    )
    assert res1.status_code == HTTPStatus.ACCEPTED
    assert res2.status_code == HTTPStatus.ACCEPTED

    # Listagem global
    response = client.get('/templates/results', headers=_auth(token))
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body['count'] >= 2

    # Filtro por doc_id
    resp_doc1 = client.get(
        '/templates/results',
        headers=_auth(token),
        params={'doc_id': doc_id1},
    )
    assert resp_doc1.status_code == HTTPStatus.OK
    body_doc1 = resp_doc1.json()
    assert body_doc1['count'] == 1
    assert body_doc1['results'][0]['doc_id'] == doc_id1

    # Filtro por status
    resp_status = client.get(
        '/templates/results',
        headers=_auth(token),
        params={'status': 'completed'},
    )
    assert resp_status.status_code == HTTPStatus.OK
    results = resp_status.json()['results']
    assert all(r['status'] == 'completed' for r in results)

    _unlink_stored(template['file_path'])



def test_get_template_compliance_by_id(client, token):
    template = _create_template(client, token)
    doc_id = str(uuid4())
    created = client.post(
        f'/templates/{doc_id}/conformidade',
        headers=_auth(token),
        data={'template_id': template['id']},
        files=_pdf_files('artigo.pdf'),
    )
    assert created.status_code == HTTPStatus.ACCEPTED
    result_id = created.json()['id']

    response = client.get(
        f'/templates/results/{result_id}', headers=_auth(token)
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == result_id
    assert data['doc_id'] == doc_id
    assert data['status'] == 'completed'
    _unlink_stored(template['file_path'])


def test_get_template_compliance_by_id_not_found(client, token):
    response = client.get(
        f'/templates/results/{uuid4()}', headers=_auth(token)
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        'detail': 'Resultado de conformidade não encontrado.'
    }


def test_delete_template_compliance(client, token):
    template = _create_template(client, token)
    doc_id = str(uuid4())
    created = client.post(
        f'/templates/{doc_id}/conformidade',
        headers=_auth(token),
        data={'template_id': template['id']},
        files=_pdf_files('artigo.pdf'),
    )
    assert created.status_code == HTTPStatus.ACCEPTED
    result_id = created.json()['id']

    # Delete
    del_resp = client.delete(
        f'/templates/results/{result_id}', headers=_auth(token)
    )
    assert del_resp.status_code == HTTPStatus.NO_CONTENT

    # Soft deleted - not found on get by id
    get_resp = client.get(
        f'/templates/results/{result_id}', headers=_auth(token)
    )
    assert get_resp.status_code == HTTPStatus.NOT_FOUND

    # Also absent from list
    list_resp = client.get(
        f'/templates/{doc_id}/conformidade', headers=_auth(token)
    )
    assert list_resp.status_code == HTTPStatus.OK
    assert list_resp.json()['count'] == 0

    _unlink_stored(template['file_path'])


def test_delete_template_compliance_not_found(client, token):
    response = client.delete(
        f'/templates/results/{uuid4()}', headers=_auth(token)
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
