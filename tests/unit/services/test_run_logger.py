from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from lumina.schemas.processing_run import (
    CriterionEvaluationRecord,
    ProcessingEvent,
    ProcessingEventType,
    ProcessingStatus,
)
from lumina.services.run_logger import RunLogger, sanitize_dict, sanitize_pii

EXPECTED_DURATION_MS = 3150
EXPECTED_SCORE = 9.5
EXPECTED_STAGES_COUNT = 3
EXPECTED_METODOLOGIA_SCORE = 8.5
EXPECTED_CRITERIA_COUNT = 3
EXPECTED_CITATIONS_COUNT = 3
EXPECTED_PURGED_COUNT = 5
EXPECTED_PURGED_AGE_COUNT = 1
EXPECTED_RETAINED_RUNS = 30
EXPECTED_RETAINED_AGE_RUNS = 1
EXPECTED_PAGES_COUNT = 12
EXPECTED_CHUNKS_COUNT = 45
EXPECTED_NULL_BYTES_COUNT = 3
EXPECTED_SECTIONS_COUNT = 2
EXPECTED_CPF_COUNT = 4
EXPECTED_EVAL_ITEMS_COUNT = 2
EXPECTED_HALLUCINATED_COUNT = 1
EXPECTED_RESOLVED_BOXES_COUNT = 2


@pytest.mark.asyncio
async def test_run_logger_lifecycle(tmp_path):
    logger = RunLogger(base_dir=tmp_path)
    run_id = uuid4()
    doc_id = uuid4()

    # 1. Iniciar run
    ev_start = await logger.start_run(
        run_id=run_id,
        document_id=doc_id,
        document_name='edital_teste.pdf',
        metadata={'version': '1.0.0'},
    )
    assert ev_start.run_id == run_id
    assert ev_start.status == ProcessingStatus.IN_PROGRESS

    # 2. Iniciar e completar etapa padrão
    await logger.start_stage(run_id=run_id, stage='extraction')
    await logger.complete_stage(
        run_id=run_id, stage='extraction', duration_ms=1200, item_count=5
    )

    # 3. Dinamismo de etapas: adicionar etapa inédita
    await logger.start_stage(run_id=run_id, stage='table_parsing')
    await logger.complete_stage(
        run_id=run_id, stage='table_parsing', duration_ms=450, item_count=2
    )

    # 4. Registrar critérios na etapa de avaliação
    await logger.start_stage(run_id=run_id, stage='evaluation')
    crit_rec = CriterionEvaluationRecord(
        criterion_id='crit_1',
        title='Qualificação Técnica',
        status=ProcessingStatus.COMPLETED,
        duration_ms=300,
        score=EXPECTED_SCORE,
        citations_count=2,
    )
    await logger.record_criterion(
        run_id=run_id, stage='evaluation', criterion_record=crit_rec
    )
    await logger.complete_stage(
        run_id=run_id,
        stage='evaluation',
        duration_ms=1500,
        item_count=1,
    )

    # 5. Completar run
    await logger.complete_run(run_id=run_id, duration_ms=EXPECTED_DURATION_MS)

    # Validar detalhamento consolidado dinamicamente
    detail = await logger.get_run_detail(run_id)
    assert detail is not None
    assert detail.id == run_id
    assert detail.release_id == run_id
    assert detail.document_id == doc_id
    assert detail.document_name == 'edital_teste.pdf'
    assert detail.status == ProcessingStatus.COMPLETED
    assert detail.duration_ms == EXPECTED_DURATION_MS

    # Validar etapas dinâmicas (inclusive table_parsing)
    stage_names = [s.name for s in detail.stages]
    assert stage_names == ['extraction', 'table_parsing', 'evaluation']

    eval_stage = next(s for s in detail.stages if s.name == 'evaluation')
    assert eval_stage.item_count == 1
    assert len(eval_stage.items) == 1
    assert eval_stage.items[0]['criterion_id'] == 'crit_1'
    assert eval_stage.items[0]['score'] == EXPECTED_SCORE

    # Validar listagem e índice
    list_resp = await logger.list_runs(limit=10, offset=0)
    assert list_resp.total == 1
    assert list_resp.items[0].id == run_id
    assert list_resp.items[0].stages_count == EXPECTED_STAGES_COUNT


@pytest.mark.asyncio
async def test_run_logger_failure_and_pii_sanitization(tmp_path):
    logger = RunLogger(base_dir=tmp_path)
    run_id = uuid4()
    doc_id = uuid4()

    await logger.start_run(run_id=run_id, document_id=doc_id)
    await logger.start_stage(run_id=run_id, stage='anonymization')

    error_msg = 'Falha no titular com CPF 123.456.789-00 e tel (21) 98765-4321'
    await logger.fail_stage(
        run_id=run_id, stage='anonymization', error=error_msg, duration_ms=100
    )
    await logger.fail_run(run_id=run_id, error=error_msg, duration_ms=150)

    detail = await logger.get_run_detail(run_id)
    assert detail is not None
    assert detail.status == ProcessingStatus.FAILED
    assert '123.456.789-00' not in detail.error_summary
    assert '[CPF_MASKED]' in detail.error_summary
    assert '[PHONE_MASKED]' in detail.error_summary

    stage = detail.stages[0]
    assert stage.status == ProcessingStatus.FAILED
    assert '[CPF_MASKED]' in stage.error_details


def test_sanitize_pii_helpers():
    text = 'CPF: 12345678901, CNPJ: 12.345.678/0001-90, Tel: 2199888-7766'
    sanitized = sanitize_pii(text)
    assert '12345678901' not in sanitized
    assert '12.345.678/0001-90' not in sanitized
    assert '[CPF_MASKED]' in sanitized
    assert '[CNPJ_MASKED]' in sanitized

    payload = {
        'info': 'CPF 111.222.333-44',
        'nested': {'contact': 'tel 21 98888-1111'},
        'list': ['111.222.333-44', 123],
        'email': 'usuario@dominio.com.br',
    }
    sanitized_dict = sanitize_dict(payload)
    assert '[CPF_MASKED]' in sanitized_dict['info']
    assert '[PHONE_MASKED]' in sanitized_dict['nested']['contact']
    assert '[CPF_MASKED]' in sanitized_dict['list'][0]
    assert '[EMAIL_MASKED]' in sanitized_dict['email']


@pytest.mark.asyncio
async def test_parallel_criteria_tracking(tmp_path):
    logger = RunLogger(base_dir=tmp_path)
    run_id = uuid4()
    doc_id = uuid4()

    await logger.start_run(run_id=run_id, document_id=doc_id)
    await logger.start_stage(run_id=run_id, stage='evaluation')

    criteria_data = [
        CriterionEvaluationRecord(
            criterion_id='crit_metodologia',
            title='Adequação Metodológica',
            status=ProcessingStatus.COMPLETED,
            duration_ms=420,
            score=8.5,
            citations_count=3,
        ),
        CriterionEvaluationRecord(
            criterion_id='crit_relevancia',
            title='Relevância Científica',
            status=ProcessingStatus.COMPLETED,
            duration_ms=390,
            score=9.0,
            citations_count=5,
        ),
        CriterionEvaluationRecord(
            criterion_id='crit_etica',
            title='Conformidade Ética',
            status=ProcessingStatus.FAILED,
            duration_ms=150,
            score=None,
            citations_count=0,
            error_message='Falta aprovação no comitê de ética',
        ),
    ]

    for crit in criteria_data:
        await logger.record_criterion(
            run_id=run_id, stage='evaluation', criterion_record=crit
        )

    await logger.complete_stage(
        run_id=run_id,
        stage='evaluation',
        duration_ms=450,
        item_count=len(criteria_data),
    )
    await logger.complete_run(run_id=run_id, duration_ms=1000)

    detail = await logger.get_run_detail(run_id)
    assert detail is not None
    eval_stage = next(s for s in detail.stages if s.name == 'evaluation')
    assert eval_stage.item_count == EXPECTED_CRITERIA_COUNT
    assert len(eval_stage.items) == EXPECTED_CRITERIA_COUNT

    metodologia = next(
        i for i in eval_stage.items if i['criterion_id'] == 'crit_metodologia'
    )
    assert metodologia['score'] == EXPECTED_METODOLOGIA_SCORE
    assert metodologia['citations_count'] == EXPECTED_CITATIONS_COUNT
    assert metodologia['status'] == ProcessingStatus.COMPLETED

    etica = next(
        i for i in eval_stage.items if i['criterion_id'] == 'crit_etica'
    )
    assert etica['status'] == ProcessingStatus.FAILED
    assert 'aprovação no comitê' in etica['error_message']


@pytest.mark.asyncio
async def test_lgpd_safeguard_zero_pii_in_jsonl(tmp_path):
    logger = RunLogger(base_dir=tmp_path)
    run_id = uuid4()
    doc_id = uuid4()

    await logger.start_run(
        run_id=run_id,
        document_id=doc_id,
        metadata={
            'coordinator_email': 'coordenador@instituto.fiocruz.br',
            'advisor_cpf': '000.111.222-33',
            'phone': '+55 21 99999-8888',
        },
    )

    await logger.start_stage(
        run_id=run_id,
        stage='evaluation',
        metadata={'reviewer_email': 'parecerista@universidade.edu.br'},
    )

    crit_with_pii = CriterionEvaluationRecord(
        criterion_id='crit_pii_check',
        title='Critério de Teste',
        status=ProcessingStatus.FAILED,
        duration_ms=100,
        error_message=('Falha CPF 999.888.777-66 e email avaliador@teste.org'),
    )
    await logger.record_criterion(
        run_id=run_id, stage='evaluation', criterion_record=crit_with_pii
    )

    await logger.complete_stage(run_id=run_id, stage='evaluation')
    await logger.complete_run(run_id=run_id)

    run_file = tmp_path / f'{run_id}.jsonl'
    raw_content = run_file.read_text(encoding='utf-8')

    assert '000.111.222-33' not in raw_content
    assert 'coordenador@instituto.fiocruz.br' not in raw_content
    assert '+55 21 99999-8888' not in raw_content
    assert 'parecerista@universidade.edu.br' not in raw_content
    assert '999.888.777-66' not in raw_content
    assert 'avaliador@teste.org' not in raw_content

    assert '[CPF_MASKED]' in raw_content
    assert '[EMAIL_MASKED]' in raw_content
    assert '[PHONE_MASKED]' in raw_content


@pytest.mark.asyncio
async def test_purge_old_runs_by_count(tmp_path):
    logger = RunLogger(base_dir=tmp_path)
    now = datetime.now(timezone.utc)
    run_ids = []

    # Criar 35 execuções com timestamps incrementais
    for i in range(35):
        r_id = uuid4()
        run_ids.append(r_id)
        start_time = now - timedelta(hours=35 - i)
        ev_start = ProcessingEvent(
            run_id=r_id,
            event=ProcessingEventType.RUN_STARTED.value,
            status=ProcessingStatus.IN_PROGRESS,
            timestamp=start_time,
            data={
                'document_id': str(uuid4()),
                'document_name': f'doc_{i}.pdf',
            },
        )
        await logger.append_event(ev_start)
        ev_end = ProcessingEvent(
            run_id=r_id,
            event=ProcessingEventType.RUN_COMPLETED.value,
            status=ProcessingStatus.COMPLETED,
            timestamp=start_time + timedelta(seconds=10),
            duration_ms=10000,
        )
        await logger.append_event(ev_end)

    # Executar purga mantendo no máximo 30 runs
    purged_count = await logger.purge_old_runs(max_runs=30, max_age_days=7)
    assert purged_count == EXPECTED_PURGED_COUNT

    # Os 5 mais antigos devem ter seus arquivos removidos
    for old_id in run_ids[:EXPECTED_PURGED_COUNT]:
        assert not logger._get_run_file(old_id).exists()

    # Os 30 mais novos devem existir
    for retained_id in run_ids[EXPECTED_PURGED_COUNT:]:
        assert logger._get_run_file(retained_id).exists()

    # Validar listagem pelo índice
    list_resp = await logger.list_runs(limit=50)
    assert list_resp.total == EXPECTED_RETAINED_RUNS


@pytest.mark.asyncio
async def test_purge_old_runs_by_age(tmp_path):
    logger = RunLogger(base_dir=tmp_path)
    now = datetime.now(timezone.utc)

    # Run antiga (10 dias atrás)
    old_id = uuid4()
    old_time = now - timedelta(days=10)
    ev_old_start = ProcessingEvent(
        run_id=old_id,
        event=ProcessingEventType.RUN_STARTED.value,
        status=ProcessingStatus.IN_PROGRESS,
        timestamp=old_time,
        data={'document_id': str(uuid4()), 'document_name': 'antigo.pdf'},
    )
    await logger.append_event(ev_old_start)
    ev_old_end = ProcessingEvent(
        run_id=old_id,
        event=ProcessingEventType.RUN_COMPLETED.value,
        status=ProcessingStatus.COMPLETED,
        timestamp=old_time + timedelta(seconds=5),
        duration_ms=5000,
    )
    await logger.append_event(ev_old_end)

    # Run recente (1 dia atrás)
    recent_id = uuid4()
    recent_time = now - timedelta(days=1)
    ev_rec_start = ProcessingEvent(
        run_id=recent_id,
        event=ProcessingEventType.RUN_STARTED.value,
        status=ProcessingStatus.IN_PROGRESS,
        timestamp=recent_time,
        data={'document_id': str(uuid4()), 'document_name': 'recente.pdf'},
    )
    await logger.append_event(ev_rec_start)
    ev_rec_end = ProcessingEvent(
        run_id=recent_id,
        event=ProcessingEventType.RUN_COMPLETED.value,
        status=ProcessingStatus.COMPLETED,
        timestamp=recent_time + timedelta(seconds=5),
        duration_ms=5000,
    )
    await logger.append_event(ev_rec_end)

    purged_count = await logger.purge_old_runs(max_runs=30, max_age_days=7)
    assert purged_count == EXPECTED_PURGED_AGE_COUNT
    assert not logger._get_run_file(old_id).exists()
    assert logger._get_run_file(recent_id).exists()

    list_resp = await logger.list_runs(limit=10)
    assert list_resp.total == EXPECTED_RETAINED_AGE_RUNS
    assert list_resp.items[0].id == recent_id


@pytest.mark.asyncio
async def test_ingestion_stages_logging_and_consolidation(tmp_path):
    logger = RunLogger(base_dir=tmp_path)
    run_id = uuid4()
    doc_id = uuid4()

    await logger.start_run(
        run_id=run_id,
        document_id=doc_id,
        document_name='edital_licitacao.pdf',
    )

    # 1. Etapa de extração e chunking
    extraction_data = {
        'pages_count': 12,
        'chunks_count': 45,
        'avg_chunk_size': 420.5,
        'extractor_type': 'PyMuPDF',
        'sanitization_ops_count': {
            'null_bytes_removed': 3,
            'whitespace_normalized': 18,
        },
    }
    await logger.start_stage(run_id=run_id, stage='extraction')
    await logger.complete_stage(
        run_id=run_id,
        stage='extraction',
        duration_ms=850,
        item_count=45,
        data=extraction_data,
    )

    # 2. Etapa de identificação de seções
    sections_data = {
        'input_window_text': 'Edital de Pregão Eletrônico...',
        'sections_detected': [
            {
                'section_name': 'DO OBJETO',
                'start_text': '1. Do objeto da licitação...',
                'end_text': None,
            },
            {
                'section_name': 'DA HABILITAÇÃO',
                'start_text': '2. Da habilitação jurídica...',
                'end_text': None,
            },
        ],
        'mapping_success_rate': 1.0,
    }
    await logger.start_stage(run_id=run_id, stage='sections')
    await logger.complete_stage(
        run_id=run_id,
        stage='sections',
        duration_ms=1400,
        item_count=2,
        data=sections_data,
    )

    # 3. Etapa de anonimização LGPD Presidio
    anonymization_data = {
        'entities_detected_count': {
            'CPF': 4,
            'CNPJ': 2,
            'PHONE': 1,
        },
        'replacement_keys': ['<CPF_1>', '<CPF_2>', '<CNPJ_1>'],
    }
    await logger.start_stage(run_id=run_id, stage='anonymization')
    await logger.complete_stage(
        run_id=run_id,
        stage='anonymization',
        duration_ms=320,
        item_count=3,
        data=anonymization_data,
    )

    await logger.complete_run(run_id=run_id, duration_ms=2570)

    # Validar consolidação na release
    detail = await logger.get_run_detail(run_id)
    assert detail is not None
    assert detail.status == ProcessingStatus.COMPLETED

    stage_names = [s.name for s in detail.stages]
    assert stage_names == ['extraction', 'sections', 'anonymization']

    # Checar detalhes da extração
    ext_stage = next(s for s in detail.stages if s.name == 'extraction')
    assert ext_stage.metadata['extractor_type'] == 'PyMuPDF'
    assert ext_stage.metadata['pages_count'] == EXPECTED_PAGES_COUNT
    assert ext_stage.metadata['chunks_count'] == EXPECTED_CHUNKS_COUNT
    assert (
        ext_stage.metadata['sanitization_ops_count']['null_bytes_removed']
        == EXPECTED_NULL_BYTES_COUNT
    )

    # Checar seções
    sec_stage = next(s for s in detail.stages if s.name == 'sections')
    assert sec_stage.metadata['mapping_success_rate'] == 1.0
    assert (
        len(sec_stage.metadata['sections_detected']) == EXPECTED_SECTIONS_COUNT
    )

    # Checar anonimização
    anon_stage = next(s for s in detail.stages if s.name == 'anonymization')
    assert (
        anon_stage.metadata['entities_detected_count']['CPF']
        == EXPECTED_CPF_COUNT
    )
    assert '<CPF_1>' in anon_stage.metadata['replacement_keys']


@pytest.mark.asyncio
async def test_evaluation_citations_and_synthesis_logging(tmp_path):
    logger = RunLogger(base_dir=tmp_path)
    run_id = uuid4()
    doc_id = uuid4()

    await logger.start_run(
        run_id=run_id,
        document_id=doc_id,
        document_name='documento_teste.pdf',
    )

    # 1. Evaluation stage com dois critérios
    await logger.start_stage(run_id=run_id, stage='evaluation')
    crit_sucesso = CriterionEvaluationRecord(
        criterion_id='crit_1',
        title='Habilitação Jurídica',
        status=ProcessingStatus.COMPLETED,
        duration_ms=120,
        score=8.5,
        citations_count=1,
        feedback='Atende plenamente aos requisitos.',
        retrieval={
            'query_executed': 'SECTION: Habilitação --- Requisito contrato',
            'initial_chunks': ['chunk_1', 'chunk_2'],
            'expanded_chunks': ['chunk_0', 'chunk_1', 'chunk_2', 'chunk_3'],
        },
        llm_interaction={
            'model': 'gpt-4o-mini',
            'prompt_rendered': 'Prompt completo do critério...',
            'raw_output': '{"score": 8.5, "fulfilled": true}',
            'tokens_prompt': 150,
            'tokens_completion': 40,
            'schema_validation_error': None,
        },
        llm_output={
            'fulfilled': True,
            'score': 8.5,
            'feedback': 'Atende plenamente aos requisitos.',
            'citations_provided': ['chunk_1'],
            'citations_hallucinated': [],
        },
    )
    crit_falha_schema = CriterionEvaluationRecord(
        criterion_id='crit_2',
        title='Qualificação Técnica',
        status=ProcessingStatus.FAILED,
        duration_ms=90,
        score=None,
        citations_count=0,
        feedback=None,
        error_message='Invalid JSON output: missing field score',
        retrieval={
            'query_executed': 'SECTION: Técnica --- Certidões',
            'initial_chunks': ['chunk_4'],
            'expanded_chunks': ['chunk_3', 'chunk_4', 'chunk_5'],
        },
        llm_interaction={
            'model': 'gpt-4o-mini',
            'prompt_rendered': 'Prompt de teste...',
            'raw_output': 'Saída truncada sem JSON',
            'tokens_prompt': 120,
            'tokens_completion': 15,
            'schema_validation_error': 'Invalid JSON: missing score',
        },
        llm_output={
            'fulfilled': False,
            'score': 0.0,
            'feedback': 'Erro na validação de schema',
            'citations_provided': ['chunk_alucinado'],
            'citations_hallucinated': ['chunk_alucinado'],
        },
    )
    await logger.record_criterion(
        run_id=run_id, stage='evaluation', criterion_record=crit_sucesso
    )
    await logger.record_criterion(
        run_id=run_id, stage='evaluation', criterion_record=crit_falha_schema
    )
    await logger.complete_stage(
        run_id=run_id,
        stage='evaluation',
        duration_ms=210,
        item_count=EXPECTED_EVAL_ITEMS_COUNT,
    )

    # 2. Citations stage
    citations_data = {
        'chunks_cited': ['chunk_1', 'chunk_alucinado'],
        'hallucinated_citations_count': EXPECTED_HALLUCINATED_COUNT,
        'resolved_boxes_count': EXPECTED_RESOLVED_BOXES_COUNT,
    }
    await logger.start_stage(run_id=run_id, stage='citations')
    await logger.complete_stage(
        run_id=run_id,
        stage='citations',
        duration_ms=45,
        item_count=EXPECTED_EVAL_ITEMS_COUNT,
        data=citations_data,
    )

    # 3. Synthesis stage
    synthesis_data = {
        'top_branches': {
            'highest_score_branch_ids': ['crit_1'],
            'lowest_score_branch_ids': ['crit_2'],
        },
        'partitioned_text': {
            'greeting': 'Olá, sou a OiacIA.',
            'fulfilled_points': 'Pontos atendidos com qualidade.',
            'improvement_points': 'Necessário aprimorar documentos.',
            'final_guidance': 'Recomenda-se revisão técnica.',
        },
    }
    await logger.start_stage(run_id=run_id, stage='synthesis')
    await logger.complete_stage(
        run_id=run_id,
        stage='synthesis',
        duration_ms=300,
        data=synthesis_data,
    )
    await logger.complete_run(run_id=run_id, duration_ms=555)

    # Verificações
    detail = await logger.get_run_detail(run_id)
    assert detail is not None
    assert detail.status == ProcessingStatus.COMPLETED

    eval_st = next(s for s in detail.stages if s.name == 'evaluation')
    assert len(eval_st.items) == EXPECTED_EVAL_ITEMS_COUNT
    c1 = next(i for i in eval_st.items if i['criterion_id'] == 'crit_1')
    assert c1['retrieval']['query_executed'].startswith('SECTION: Habilitação')
    assert c1['llm_interaction']['model'] == 'gpt-4o-mini'
    assert c1['llm_output']['fulfilled'] is True
    assert c1['llm_output']['citations_provided'] == ['chunk_1']

    c2 = next(i for i in eval_st.items if i['criterion_id'] == 'crit_2')
    assert c2['status'] == ProcessingStatus.FAILED
    assert c2['llm_interaction']['schema_validation_error'] is not None
    assert c2['llm_output']['citations_hallucinated'] == ['chunk_alucinado']

    cit_st = next(s for s in detail.stages if s.name == 'citations')
    assert (
        cit_st.metadata['hallucinated_citations_count']
        == EXPECTED_HALLUCINATED_COUNT
    )
    assert (
        cit_st.metadata['resolved_boxes_count']
        == EXPECTED_RESOLVED_BOXES_COUNT
    )

    synth_st = next(s for s in detail.stages if s.name == 'synthesis')
    assert synth_st.metadata['top_branches']['highest_score_branch_ids'] == [
        'crit_1'
    ]
    assert (
        synth_st.metadata['partitioned_text']['greeting']
        == 'Olá, sou a OiacIA.'
    )
