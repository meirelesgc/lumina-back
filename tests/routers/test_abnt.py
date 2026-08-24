from http import HTTPStatus
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from lumina.features import abnt_conformity_service

PDF_BYTES = b'%PDF-1.4 dummy article'


def _auth(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def _pdf_files(filename: str = 'artigo.pdf') -> dict:
    return {'file': (filename, PDF_BYTES, 'application/pdf')}


@pytest.fixture(autouse=True)
def isolate_abnt_store(tmp_path, monkeypatch):
    uploads = tmp_path / 'uploads'
    uploads.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(abnt_conformity_service, 'UPLOADS_DIR', uploads)


@pytest.fixture(autouse=True)
def mock_abnt_compare(mocker):
    report = MagicMock()
    report.model_dump.return_value = {
        'metadata': {
            'approach': 'prompt',
            'model': 'test',
            'article_file': 'artigo.pdf',
        },
        'summary': {
            'is_compliant': True,
            'criteria_total': 0,
            'criteria_passed': 0,
            'description': 'ok',
        },
        'criteria': [],
    }
    mocker.patch(
        'lumina.features.abnt_conformity_service.abnt_check.compare',
        return_value=report,
    )


def test_process_abnt_compliance_unauthorized(client):
    response = client.post(
        f'/abnt/{uuid4()}/conformidade',
        files=_pdf_files(),
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_abnt_compliance_unauthorized(client):
    response = client.get(f'/abnt/{uuid4()}/conformidade')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_list_abnt_compliance_unauthorized(client):
    response = client.get('/abnt/results')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_abnt_compliance_by_id_unauthorized(client):
    response = client.get(f'/abnt/results/{uuid4()}')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_delete_abnt_compliance_unauthorized(client):
    response = client.delete(f'/abnt/results/{uuid4()}')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_abnt_compliance_empty(client, token):
    doc_id = str(uuid4())
    response = client.get(
        f'/abnt/{doc_id}/conformidade', headers=_auth(token)
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'count': 0, 'results': []}


def test_process_abnt_compliance(client, token):
    doc_id = str(uuid4())
    response = client.post(
        f'/abnt/{doc_id}/conformidade',
        headers=_auth(token),
        files=_pdf_files('artigo.pdf'),
    )

    assert response.status_code == HTTPStatus.ACCEPTED
    data = response.json()
    assert data['doc_id'] == doc_id
    assert data['status'] == 'processing'
    assert data['file_path'].startswith('abnt_conformity/uploads/')
    assert 'id' in data
    assert 'created_at' in data


def test_process_abnt_compliance_missing_file(client, token):
    response = client.post(
        f'/abnt/{uuid4()}/conformidade',
        headers=_auth(token),
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_get_abnt_compliance_after_process(client, token):
    doc_id = str(uuid4())
    accepted = client.post(
        f'/abnt/{doc_id}/conformidade',
        headers=_auth(token),
        files=_pdf_files('artigo.pdf'),
    )
    assert accepted.status_code == HTTPStatus.ACCEPTED

    response = client.get(
        f'/abnt/{doc_id}/conformidade', headers=_auth(token)
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body['count'] == 1
    result = body['results'][0]
    assert result['id'] == accepted.json()['id']
    assert result['doc_id'] == doc_id
    assert result['status'] == 'completed'
    assert result['report']['summary']['is_compliant'] is True


def test_get_abnt_compliance_newest_first(client, token):
    doc_id = str(uuid4())
    first = client.post(
        f'/abnt/{doc_id}/conformidade',
        headers=_auth(token),
        files=_pdf_files('artigo1.pdf'),
    )
    second = client.post(
        f'/abnt/{doc_id}/conformidade',
        headers=_auth(token),
        files=_pdf_files('artigo2.pdf'),
    )

    response = client.get(
        f'/abnt/{doc_id}/conformidade', headers=_auth(token)
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    expected_ids = [second.json()['id'], first.json()['id']]
    assert body['count'] == len(expected_ids)
    ids = [item['id'] for item in body['results']]
    assert ids == expected_ids


def test_get_abnt_compliance_filters_by_doc_id(client, token):
    first_doc = str(uuid4())
    second_doc = str(uuid4())
    client.post(
        f'/abnt/{first_doc}/conformidade',
        headers=_auth(token),
        files=_pdf_files(),
    )
    client.post(
        f'/abnt/{second_doc}/conformidade',
        headers=_auth(token),
        files=_pdf_files(),
    )

    response = client.get(
        f'/abnt/{first_doc}/conformidade', headers=_auth(token)
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body['count'] == 1
    assert body['results'][0]['doc_id'] == first_doc


def test_list_abnt_compliance_global_and_filters(client, token):
    doc_id1 = str(uuid4())
    doc_id2 = str(uuid4())

    res1 = client.post(
        f'/abnt/{doc_id1}/conformidade',
        headers=_auth(token),
        files=_pdf_files('artigo1.pdf'),
    )
    res2 = client.post(
        f'/abnt/{doc_id2}/conformidade',
        headers=_auth(token),
        files=_pdf_files('artigo2.pdf'),
    )
    assert res1.status_code == HTTPStatus.ACCEPTED
    assert res2.status_code == HTTPStatus.ACCEPTED

    # Listagem global
    response = client.get('/abnt/results', headers=_auth(token))
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body['count'] >= 2

    # Filtro por doc_id
    resp_doc1 = client.get(
        '/abnt/results',
        headers=_auth(token),
        params={'doc_id': doc_id1},
    )
    assert resp_doc1.status_code == HTTPStatus.OK
    body_doc1 = resp_doc1.json()
    assert body_doc1['count'] == 1
    assert body_doc1['results'][0]['doc_id'] == doc_id1

    # Filtro por status
    resp_status = client.get(
        '/abnt/results',
        headers=_auth(token),
        params={'status': 'completed'},
    )
    assert resp_status.status_code == HTTPStatus.OK
    results = resp_status.json()['results']
    assert all(r['status'] == 'completed' for r in results)


def test_get_abnt_compliance_by_id(client, token):
    doc_id = str(uuid4())
    created = client.post(
        f'/abnt/{doc_id}/conformidade',
        headers=_auth(token),
        files=_pdf_files('artigo.pdf'),
    )
    assert created.status_code == HTTPStatus.ACCEPTED
    result_id = created.json()['id']

    response = client.get(
        f'/abnt/results/{result_id}', headers=_auth(token)
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == result_id
    assert data['doc_id'] == doc_id
    assert data['status'] == 'completed'


def test_get_abnt_compliance_by_id_not_found(client, token):
    response = client.get(
        f'/abnt/results/{uuid4()}', headers=_auth(token)
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        'detail': 'Resultado de conformidade não encontrado.'
    }


def test_delete_abnt_compliance(client, token):
    doc_id = str(uuid4())
    created = client.post(
        f'/abnt/{doc_id}/conformidade',
        headers=_auth(token),
        files=_pdf_files('artigo.pdf'),
    )
    assert created.status_code == HTTPStatus.ACCEPTED
    result_id = created.json()['id']

    # Delete
    del_resp = client.delete(
        f'/abnt/results/{result_id}', headers=_auth(token)
    )
    assert del_resp.status_code == HTTPStatus.NO_CONTENT

    # Soft deleted - not found on get by id
    get_resp = client.get(
        f'/abnt/results/{result_id}', headers=_auth(token)
    )
    assert get_resp.status_code == HTTPStatus.NOT_FOUND

    # Also absent from list
    list_resp = client.get(
        f'/abnt/{doc_id}/conformidade', headers=_auth(token)
    )
    assert list_resp.status_code == HTTPStatus.OK
    assert list_resp.json()['count'] == 0


def test_delete_abnt_compliance_not_found(client, token):
    response = client.delete(
        f'/abnt/results/{uuid4()}', headers=_auth(token)
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
