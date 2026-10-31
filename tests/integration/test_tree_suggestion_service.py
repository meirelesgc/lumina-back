import asyncio
from datetime import datetime, timedelta, timezone
from functools import partial
from http import HTTPStatus
from io import BytesIO
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import BackgroundTasks, HTTPException, UploadFile
from starlette.datastructures import Headers

from lumina.models import (
    Branch,
    Source,
    Taxonomy,
    TaxonomySource,
    TreeSuggestionSession,
    Typification,
    TypificationSource,
)
from lumina.schemas import TreeSuggestionItemConfirm
from lumina.services import tree_suggestion_service as service
from lumina.services.ai.tree_suggestion import generate_tree_suggestions
from lumina.services.ai.tree_suggestion.structures import (
    ConsolidatedBranch,
    ConsolidatedTaxonomy,
    ConsolidationResult,
    RuleBatchResult,
)
from tests.factories.tree_suggestion_factory import (
    ESTRUTURA,
    INTRODUCAO,
    METODOLOGIA,
    TCC,
    FakeStructuredModel,
    build_normative_pdf,
    default_create_responses,
    rule,
)

PENDING_TASK_TURNS = 5


class FakeStorage:
    def __init__(self):
        self.saved = []

    async def save(self, file, filename):
        self.saved.append(filename)
        return f'/uploads/{filename}'


def _upload(content: bytes, content_type='application/pdf', name='n.pdf'):
    return UploadFile(
        file=BytesIO(content),
        filename=name,
        headers=Headers({'content-type': content_type}),
    )


@pytest.fixture
def pdf_path(tmp_path):
    return build_normative_pdf(tmp_path / 'regulamento.pdf')


@pytest.fixture
def fake_generation(monkeypatch, pdf_path):
    """Gera com modelo fake e lê o PDF de teste no lugar do storage."""
    responses = default_create_responses()
    model = FakeStructuredModel(responses)
    monkeypatch.setattr(service, '_local_path', lambda _: str(pdf_path))
    monkeypatch.setattr(
        service,
        'generate_tree_suggestions',
        partial(generate_tree_suggestions, model=model, fast_model=model),
    )
    return responses


async def _new_session(session, user, typification_id=None):
    suggestion = TreeSuggestionSession(
        mode='enrich' if typification_id else 'create',
        file_path='/uploads/regulamento.pdf',
        original_filename='regulamento.pdf',
        target_typification_id=typification_id,
        processing_started_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    suggestion.set_creation_audit(user.id)
    session.add(suggestion)
    await session.commit()
    return suggestion


@pytest_asyncio.fixture
async def ready_session(session, user, fake_generation):
    suggestion = await _new_session(session, user)
    await service._generate_items(session, suggestion.id)
    detail = await service.get_session_detail(session, suggestion.id)
    assert detail.status == 'ready'
    return detail


def _item(detail, kind, title=None):
    return next(
        i
        for i in detail.items
        if i.kind == kind and (title is None or i.proposed_title == title)
    )


# --- 5.1 Criação -----------------------------------------------------------


@pytest.mark.asyncio
async def test_create_session_success(session, user, pdf_path):
    background_tasks = BackgroundTasks()

    detail = await service.create_session(
        session,
        user.id,
        FakeStorage(),
        _upload(pdf_path.read_bytes()),
        background_tasks=background_tasks,
    )

    assert detail.status == 'processing'
    assert detail.mode == 'create'
    assert detail.page_count == 4  # noqa: PLR2004
    assert detail.created_by == user.id
    assert detail.file_path.startswith('/uploads/')
    assert len(background_tasks.tasks) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('content', 'content_type'),
    [
        (b'%PDF-1.7 corrompido', 'text/plain'),
        (b'nao e pdf', 'application/pdf'),
    ],
)
async def test_create_session_rejects_non_pdf(
    session, user, content, content_type
):
    with pytest.raises(HTTPException) as exc:
        await service.create_session(
            session, user.id, FakeStorage(), _upload(content, content_type)
        )
    assert exc.value.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE


@pytest.mark.asyncio
async def test_create_session_rejects_too_many_pages(
    session, user, pdf_path, monkeypatch
):
    monkeypatch.setattr(service.SETTINGS, 'TREE_SUGGESTION_MAX_PAGES', 2)

    with pytest.raises(HTTPException) as exc:
        await service.create_session(
            session, user.id, FakeStorage(), _upload(pdf_path.read_bytes())
        )
    assert exc.value.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE


@pytest.mark.asyncio
async def test_create_session_rejects_large_file(
    session, user, pdf_path, monkeypatch
):
    monkeypatch.setattr(service, 'BYTES_PER_MB', 1)
    monkeypatch.setattr(service.SETTINGS, 'TREE_SUGGESTION_MAX_FILE_MB', 10)

    with pytest.raises(HTTPException) as exc:
        await service.create_session(
            session, user.id, FakeStorage(), _upload(pdf_path.read_bytes())
        )
    assert exc.value.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE


@pytest.mark.asyncio
async def test_create_session_unknown_typification(session, user, pdf_path):
    with pytest.raises(HTTPException) as exc:
        await service.create_session(
            session,
            user.id,
            FakeStorage(),
            _upload(pdf_path.read_bytes()),
            typification_id=uuid4(),
        )
    assert exc.value.status_code == HTTPStatus.NOT_FOUND


# --- 5.2 / 5.3 Processamento e leitura -------------------------------------


@pytest.mark.asyncio
async def test_generation_success_creates_pending_items(ready_session):
    kinds = [i.kind for i in ready_session.items]

    assert kinds.count('source') == 1
    assert kinds.count('typification') == 2  # noqa: PLR2004
    assert all(i.status == 'pending' for i in ready_session.items)
    assert ready_session.generation_model == 'fake-model'
    branch = _item(ready_session, 'branch', INTRODUCAO)
    assert branch.evidence[0].pages == [4]


@pytest.mark.asyncio
async def test_generation_reports_formatting_rules(ready_session):
    titles = {i.proposed_title for i in ready_session.items}

    assert [r.title for r in ready_session.excluded_rules] == [
        'Fonte Arial 12',
        'Margens de 3 cm',
    ]
    assert ready_session.excluded_rules[0].pages == [2]
    assert not titles & {'Fonte Arial 12', 'Margens de 3 cm', 'Formatação'}


@pytest.mark.asyncio
async def test_generation_without_rules_keeps_only_source(
    session, user, fake_generation
):
    fake_generation[RuleBatchResult] = RuleBatchResult(rules=[])
    suggestion = await _new_session(session, user)

    await service._generate_items(session, suggestion.id)
    detail = await service.get_session_detail(session, suggestion.id)

    assert detail.status == 'ready'
    assert [i.kind for i in detail.items] == ['source']
    assert detail.excluded_rules == []


@pytest.mark.asyncio
async def test_generation_failure_marks_session_failed(
    session, user, fake_generation
):
    fake_generation[RuleBatchResult] = RuntimeError('LLM fora do ar')
    suggestion = await _new_session(session, user)

    await service._generate_items(session, suggestion.id)
    detail = await service.get_session_detail(session, suggestion.id)

    assert detail.status == 'failed'
    assert detail.error_message == (
        'Não foi possível extrair regras do documento.'
    )
    assert detail.items == []


@pytest.mark.asyncio
async def test_stale_processing_session_is_reported_failed(session, user):
    suggestion = await _new_session(session, user)
    suggestion.processing_started_at = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) - timedelta(hours=2)
    await session.commit()

    detail = await service.get_session_detail(session, suggestion.id)

    assert detail.status == 'failed'
    assert detail.error_message == service.TIMEOUT_FAILURE


# --- 5.4 Confirmação -------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_create_with_edits(session, user, ready_session):
    typ = _item(ready_session, 'typification', TCC)

    item = await service.confirm_item(
        session,
        user.id,
        ready_session.id,
        typ.id,
        TreeSuggestionItemConfirm(title='TCC de Graduação'),
    )

    assert item.status == 'confirmed'
    assert item.final_title == 'TCC de Graduação'
    created = await session.get(Typification, item.applied_entity_id)
    assert created.name == 'TCC de Graduação'
    assert item.reviewed_by == user.id


@pytest.mark.asyncio
async def test_confirm_child_requires_confirmed_parent(
    session, user, ready_session
):
    taxonomy = _item(ready_session, 'taxonomy', ESTRUTURA)

    with pytest.raises(HTTPException) as exc:
        await service.confirm_item(
            session, user.id, ready_session.id, taxonomy.id
        )
    assert exc.value.status_code == HTTPStatus.CONFLICT


@pytest.mark.asyncio
async def test_revisor_confirma_cadeia_de_sugestoes_sem_chamar_modelo(
    session, user, ready_session, mock_fast_model_for_tests
):
    typ = _item(ready_session, 'typification', TCC)
    taxonomy = _item(ready_session, 'taxonomy', ESTRUTURA)
    branch = _item(ready_session, 'branch', INTRODUCAO)
    mock_fast_model_for_tests.reset_mock()

    await service.confirm_item(session, user.id, ready_session.id, typ.id)
    tax_item = await service.confirm_item(
        session, user.id, ready_session.id, taxonomy.id
    )
    branch_item = await service.confirm_item(
        session, user.id, ready_session.id, branch.id
    )
    # Dá a vez às tarefas que uma confirmação tenha agendado em segundo plano.
    for _ in range(PENDING_TASK_TURNS):
        await asyncio.sleep(0)

    created = await session.get(Branch, branch_item.applied_entity_id)
    assert created.taxonomy_id == tax_item.applied_entity_id
    mock_fast_model_for_tests.with_structured_output.assert_not_called()


@pytest.mark.asyncio
async def test_confirm_title_collision_keeps_item_pending(
    session, user, ready_session
):
    session.add(Typification(name=TCC))
    await session.commit()
    typ = _item(ready_session, 'typification', TCC)

    with pytest.raises(HTTPException) as exc:
        await service.confirm_item(session, user.id, ready_session.id, typ.id)

    assert exc.value.status_code == HTTPStatus.CONFLICT
    detail = await service.get_session_detail(session, ready_session.id)
    assert _item(detail, 'typification', TCC).status == 'pending'


@pytest.mark.asyncio
async def test_confirm_not_pending_and_not_ready(session, user, ready_session):
    source = _item(ready_session, 'source')
    await service.discard_item(session, user.id, ready_session.id, source.id)

    with pytest.raises(HTTPException) as exc:
        await service.confirm_item(
            session, user.id, ready_session.id, source.id
        )
    assert exc.value.status_code == HTTPStatus.CONFLICT

    processing = await _new_session(session, user)
    with pytest.raises(HTTPException) as exc:
        await service.confirm_item(session, user.id, processing.id, uuid4())
    assert exc.value.status_code == HTTPStatus.CONFLICT


async def _enrich_session(session, user, fake_generation):
    typification = Typification(name=TCC)
    session.add(typification)
    await session.flush()
    taxonomy = Taxonomy(
        title=ESTRUTURA,
        description='Seções obrigatórias do trabalho.',
        typification_id=typification.id,
    )
    session.add(taxonomy)
    await session.flush()
    branch = Branch(
        title='Introdução', description='Introdução.', taxonomy_id=taxonomy.id
    )
    session.add(branch)
    await session.commit()

    fake_generation[RuleBatchResult] = RuleBatchResult(
        rules=[
            rule(
                TCC,
                ESTRUTURA,
                INTRODUCAO,
                'A introdução deve apresentar o objetivo geral do trabalho.',
            ),
            rule(
                TCC,
                ESTRUTURA,
                METODOLOGIA,
                'A metodologia deve descrever os procedimentos de coleta de '
                'dados.',
            ),
        ]
    )
    fake_generation[ConsolidationResult] = ConsolidationResult(
        taxonomies=[
            ConsolidatedTaxonomy(
                title=ESTRUTURA,
                description='Seções obrigatórias do trabalho.',
                decision='same',
                existing_id='T1',
                branches=[
                    ConsolidatedBranch(
                        title=INTRODUCAO,
                        description='Objetivo geral.',
                        candidate_ids=[1],
                        decision='update',
                        existing_id='B1',
                    ),
                    ConsolidatedBranch(
                        title=METODOLOGIA,
                        description='Procedimentos de coleta.',
                        candidate_ids=[2],
                    ),
                ],
            )
        ]
    )
    suggestion = await _new_session(session, user, typification.id)
    await service._generate_items(session, suggestion.id)
    detail = await service.get_session_detail(session, suggestion.id)
    return detail, typification, taxonomy, branch


@pytest.mark.asyncio
async def test_enrich_update_and_create_under_existing(
    session, user, fake_generation
):
    detail, typification, taxonomy, branch = await _enrich_session(
        session, user, fake_generation
    )
    assert detail.target_typification_name == TCC
    update = _item(detail, 'branch', INTRODUCAO)
    new_branch = _item(detail, 'branch', METODOLOGIA)
    assert update.operation == 'update'
    assert update.target_snapshot['title'] == 'Introdução'
    assert new_branch.parent_entity_title == ESTRUTURA

    await service.confirm_item(session, user.id, detail.id, update.id)
    created = await service.confirm_item(
        session, user.id, detail.id, new_branch.id
    )

    await session.refresh(branch)
    assert branch.title == INTRODUCAO
    applied = await session.get(Branch, created.applied_entity_id)
    assert applied.taxonomy_id == taxonomy.id


@pytest.mark.asyncio
async def test_enrich_stale_update_is_rejected(session, user, fake_generation):
    detail, _, _, branch = await _enrich_session(
        session, user, fake_generation
    )
    branch.description = 'Alterada por outra pessoa.'
    await session.commit()
    update = _item(detail, 'branch', INTRODUCAO)

    with pytest.raises(HTTPException) as exc:
        await service.confirm_item(session, user.id, detail.id, update.id)

    assert exc.value.status_code == HTTPStatus.CONFLICT
    await session.refresh(branch)
    assert branch.title == 'Introdução'


# --- 5.5 Vínculo com o Source ---------------------------------------------


@pytest.mark.asyncio
async def test_source_confirmed_after_tree_items_links_them(
    session, user, ready_session
):
    typ = _item(ready_session, 'typification', TCC)
    taxonomy = _item(ready_session, 'taxonomy', ESTRUTURA)
    typ_item = await service.confirm_item(
        session, user.id, ready_session.id, typ.id
    )
    tax_item = await service.confirm_item(
        session, user.id, ready_session.id, taxonomy.id
    )

    source_item = await service.confirm_item(
        session, user.id, ready_session.id, _item(ready_session, 'source').id
    )

    source = await session.get(Source, source_item.applied_entity_id)
    assert source.file_path == ready_session.file_path
    assert await session.get(
        TypificationSource, (typ_item.applied_entity_id, source.id)
    )
    assert await session.get(
        TaxonomySource, (tax_item.applied_entity_id, source.id)
    )


@pytest.mark.asyncio
async def test_tree_item_confirmed_after_source_is_linked(
    session, user, ready_session
):
    source_item = await service.confirm_item(
        session, user.id, ready_session.id, _item(ready_session, 'source').id
    )
    typ_item = await service.confirm_item(
        session,
        user.id,
        ready_session.id,
        _item(ready_session, 'typification', TCC).id,
    )

    assert await session.get(
        TypificationSource,
        (typ_item.applied_entity_id, source_item.applied_entity_id),
    )


@pytest.mark.asyncio
async def test_discarded_source_creates_no_links(session, user, ready_session):
    await service.discard_item(
        session, user.id, ready_session.id, _item(ready_session, 'source').id
    )
    typ_item = await service.confirm_item(
        session,
        user.id,
        ready_session.id,
        _item(ready_session, 'typification', TCC).id,
    )

    typification = await session.get(Typification, typ_item.applied_entity_id)
    await session.refresh(typification, ['sources'])
    assert typification.sources == []


# --- 5.6 Descarte ---------------------------------------------------------


@pytest.mark.asyncio
async def test_discard_parent_cascades(session, user, ready_session):
    typ = _item(ready_session, 'typification', TCC)

    detail = await service.discard_item(
        session, user.id, ready_session.id, typ.id
    )

    descendants = {i.id for i in detail.items if i.parent_item_id == typ.id}
    descendants |= {
        i.id for i in detail.items if i.parent_item_id in descendants
    }
    statuses = {i.id: i.status for i in detail.items}
    assert statuses[typ.id] == 'discarded'
    assert descendants
    assert all(statuses[i] == 'discarded' for i in descendants)
    assert _item(detail, 'source').status == 'pending'


@pytest.mark.asyncio
async def test_discard_session_keeps_confirmed(session, user, ready_session):
    source = _item(ready_session, 'source')
    await service.confirm_item(session, user.id, ready_session.id, source.id)

    detail = await service.discard_session(session, user.id, ready_session.id)

    assert detail.status == 'completed'
    assert _item(detail, 'source').status == 'confirmed'
    assert all(
        i.status == 'discarded' for i in detail.items if i.kind != 'source'
    )


@pytest.mark.asyncio
async def test_session_completes_after_last_review(
    session, user, fake_generation
):
    fake_generation[RuleBatchResult] = RuleBatchResult(rules=[])
    suggestion = await _new_session(session, user)
    await service._generate_items(session, suggestion.id)
    detail = await service.get_session_detail(session, suggestion.id)

    await service.confirm_item(
        session, user.id, suggestion.id, _item(detail, 'source').id
    )

    detail = await service.get_session_detail(session, suggestion.id)
    assert detail.status == 'completed'
