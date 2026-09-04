from http import HTTPStatus
from uuid import uuid4

import pytest
import pytest_asyncio

from lumina.core.security import create_access_token
from lumina.models import User
from lumina.schemas.processing_run import (
    CriterionEvaluationRecord,
    ProcessingStatus,
)
from lumina.schemas.user import AccessType
from lumina.services.run_logger import RunLogger

CRIT_SCORE = 8.5
RUN_DURATION_MS = 2500
EXPECTED_STAGES_COUNT = 3
MIN_EVENTS_COUNT = 6


@pytest_asyncio.fixture
async def admin_user(session):
    admin = User(
        username=f'admin_{uuid4().hex[:6]}',
        email=f'admin_{uuid4().hex[:6]}@test.com',
        phone_number='5501999998888',
        password='hash',
        access_level=AccessType.ADMIN,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


@pytest.fixture
def admin_token(admin_user):
    return create_access_token({'sub': str(admin_user.id)})


@pytest.mark.asyncio
async def test_processing_runs_security_rbac(client, token):
    # 1. Sem token -> 401 Unauthorized
    resp_unauth = client.get('/processing-runs')
    assert resp_unauth.status_code == HTTPStatus.UNAUTHORIZED

    # 2. Usuário comum (não admin) -> 403 Forbidden
    resp_forbidden = client.get(
        '/processing-runs',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp_forbidden.status_code == HTTPStatus.FORBIDDEN
    detail = resp_forbidden.json()['detail']
    assert 'restricted to system administrators' in detail


async def _seed_test_run(logger, release_id, doc_id):
    await logger.start_run(
        run_id=release_id,
        document_id=doc_id,
        document_name='edital_auditoria.pdf',
    )
    await logger.start_stage(run_id=release_id, stage='extraction')
    await logger.complete_stage(
        run_id=release_id, stage='extraction', duration_ms=500
    )
    await logger.start_stage(run_id=release_id, stage='citation_tracking')
    await logger.complete_stage(
        run_id=release_id, stage='citation_tracking', duration_ms=300
    )
    await logger.start_stage(run_id=release_id, stage='evaluation')
    crit = CriterionEvaluationRecord(
        criterion_id='c_101',
        title='Experiência Prévia',
        status=ProcessingStatus.COMPLETED,
        duration_ms=400,
        score=CRIT_SCORE,
        citations_count=3,
    )
    await logger.record_criterion(
        run_id=release_id, stage='evaluation', criterion_record=crit
    )
    await logger.complete_stage(
        run_id=release_id, stage='evaluation', duration_ms=900, item_count=1
    )
    await logger.complete_run(run_id=release_id, duration_ms=RUN_DURATION_MS)


@pytest.mark.asyncio
async def test_processing_runs_admin_list_and_details(
    client, admin_token, monkeypatch, tmp_path
):
    test_logger = RunLogger(base_dir=tmp_path)
    monkeypatch.setattr(
        'lumina.routers.processing_runs.get_run_logger', lambda: test_logger
    )

    release_id = uuid4()
    doc_id = uuid4()
    await _seed_test_run(test_logger, release_id, doc_id)

    headers = {'Authorization': f'Bearer {admin_token}'}

    # 1. Listagem
    resp_list = client.get('/processing-runs', headers=headers)
    assert resp_list.status_code == HTTPStatus.OK
    data_list = resp_list.json()
    assert data_list['total'] == 1
    item = data_list['items'][0]
    assert item['id'] == str(release_id)
    assert item['stages_count'] == EXPECTED_STAGES_COUNT

    # 2. Detalhe e dinamismo de etapas
    resp_detail = client.get(f'/processing-runs/{release_id}', headers=headers)
    assert resp_detail.status_code == HTTPStatus.OK
    data_detail = resp_detail.json()
    stage_names = [s['name'] for s in data_detail['stages']]
    assert stage_names == ['extraction', 'citation_tracking', 'evaluation']

    eval_stage = data_detail['stages'][2]
    assert eval_stage['items'][0]['criterion_id'] == 'c_101'

    # 3. Eventos brutos
    resp_events = client.get(
        f'/processing-runs/{release_id}/events', headers=headers
    )
    assert resp_events.status_code == HTTPStatus.OK
    assert len(resp_events.json()) >= MIN_EVENTS_COUNT

    # 4. 404 para inexistente
    resp_not_found = client.get(f'/processing-runs/{uuid4()}', headers=headers)
    assert resp_not_found.status_code == HTTPStatus.NOT_FOUND
