from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from langchain_core.documents import Document

from lumina.schemas.processing_run import ProcessingStatus
from lumina.services.ai.stages.evaluation import (
    evaluate_criteria_batch as apply_tree,
)
from lumina.services.ai.stages.retrieval import (
    format_context,
    retrieve_evaluation_payloads,
)
from lumina.services.ai.stages.synthesis import partition_synthesis_text
from lumina.services.run_logger import RunLogger

EXPECTED_SCORE_NINE = 9
EXPECTED_REFS_COUNT_ONE = 1
EXPECTED_ITEMS_COUNT_TWO = 2


@pytest.mark.asyncio
async def test_apply_tree_resolves_citations_into_references():
    mock_chain = MagicMock()
    mock_chain.abatch = AsyncMock(
        return_value=[
            {
                'feedback': 'O resumo possui boa redação.',
                'fulfilled': True,
                'score': 9,
                'citations': [
                    {
                        'chunk_id': 'chunk_0_1',
                        'text_snippet': 'Texto do resumo',
                    },
                    {
                        'chunk_id': 'chunk_fantasma',
                        'text_snippet': 'Inexistente',
                    },
                ],
            }
        ]
    )

    mock_chunk = Document(
        page_content='Texto do resumo com coordenadas',
        metadata={
            'chunk_id': 'chunk_0_1',
            'page': 0,
            'rects': [[10.0, 20.0, 100.0, 40.0]],
        },
    )

    eval_args = [
        {
            'id': 'mock-branch-id',
            'document': '[FONTE] chunk_id: chunk_0_1\nTexto do resumo',
            'source': 'Fonte 1',
            'requirement': 'Redação: concisa',
            'expected_section': 'Resumo',
            'query': 'Analise o item',
            '_chunks': [mock_chunk],
        }
    ]

    result = await apply_tree(mock_chain, eval_args)

    assert len(result) == 1
    item = result[0]
    assert item['score'] == EXPECTED_SCORE_NINE
    assert item['fulfilled'] is True
    assert 'references' in item
    assert len(item['references']) == 1
    assert item['references'][0]['chunk_id'] == 'chunk_0_1'
    assert item['references'][0]['page'] == 0
    assert item['references'][0]['rects'] == [
        {'x1': 10.0, 'y1': 20.0, 'x2': 100.0, 'y2': 40.0}
    ]


def test_partition_synthesis_text_full():
    sample_text = (
        'Olá, sou OiacIA, assistente de análise técnica.\n\n'
        '# Pontos atendidos\n'
        'O documento demonstra boa estrutura e atende aos editais.\n\n'
        '# Pontos a aprimorar\n'
        'Falta detalhar metodologia e cronograma financeiro.\n\n'
        '# Orientação final\n'
        'Recomenda-se revisão técnica antes da submissão.'
    )
    result = partition_synthesis_text(sample_text)
    assert 'Olá, sou OiacIA' in result['greeting']
    assert 'boa estrutura' in result['fulfilled_points']
    assert 'metodologia' in result['improvement_points']
    assert 'revisão técnica' in result['final_guidance']


def test_partition_synthesis_text_empty():
    result = partition_synthesis_text('')
    assert not result['greeting']
    assert not result['fulfilled_points']
    assert not result['improvement_points']
    assert not result['final_guidance']


@pytest.mark.asyncio
async def test_apply_tree_isolates_schema_validation_error(
    tmp_path, monkeypatch
):
    logger = RunLogger(base_dir=tmp_path)
    monkeypatch.setattr(
        'lumina.services.ai.stages.evaluation.get_run_logger',
        lambda: logger,
    )
    run_id = uuid4()
    await logger.start_run(run_id=run_id, document_id=uuid4())
    await logger.start_stage(run_id=run_id, stage='evaluation')

    mock_prompt = MagicMock()
    mock_model = MagicMock()
    mock_parser = MagicMock()

    mock_prompt.__or__ = MagicMock(return_value=mock_model)
    mock_model.abatch = AsyncMock(
        return_value=[
            MagicMock(content='{"score": 9, "fulfilled": true}'),
            MagicMock(content='Saída mal formatada que quebra o parse'),
        ]
    )
    mock_model.model_name = 'mock-llm'

    def mock_parse(raw):
        if 'mal formatada' in raw:
            raise ValueError('Invalid JSON schema: missing field score')
        return {
            'score': EXPECTED_SCORE_NINE,
            'fulfilled': True,
            'feedback': 'Critério válido',
            'citations': [{'chunk_id': 'chunk_valido'}],
        }

    mock_parser.parse = MagicMock(side_effect=mock_parse)

    mock_chain = MagicMock()
    mock_chain.steps = [mock_prompt, mock_model, mock_parser]

    valid_chunk = Document(
        page_content='Texto válido',
        metadata={
            'chunk_id': 'chunk_valido',
            'page': 0,
            'rects': [[0.0, 0.0, 1.0, 1.0]],
        },
    )

    eval_args = [
        {
            'id': 'branch_ok',
            'document': 'doc 1',
            'source': 'fonte',
            'requirement': 'req 1',
            'expected_section': 'Sessao 1',
            'query': 'query 1',
            '_chunks': [valid_chunk],
        },
        {
            'id': 'branch_broken',
            'document': 'doc 2',
            'source': 'fonte',
            'requirement': 'req 2',
            'expected_section': 'Sessao 2',
            'query': 'query 2',
            '_chunks': [],
        },
    ]

    result = await apply_tree(mock_chain, eval_args, run_id=run_id)

    assert len(result) == EXPECTED_ITEMS_COUNT_TWO
    ok_item = next(r for r in result if r['id'] == 'branch_ok')
    assert ok_item['score'] == EXPECTED_SCORE_NINE
    assert ok_item['fulfilled'] is True
    assert len(ok_item['references']) == EXPECTED_REFS_COUNT_ONE

    broken_item = next(r for r in result if r['id'] == 'branch_broken')
    assert broken_item['fulfilled'] is False
    assert 'Erro na validação de schema' in broken_item['feedback']

    await logger.complete_stage(run_id=run_id, stage='evaluation')
    await logger.complete_run(run_id=run_id)

    detail = await logger.get_run_detail(run_id)
    assert detail is not None
    eval_stage = next(s for s in detail.stages if s.name == 'evaluation')
    assert len(eval_stage.items) == EXPECTED_ITEMS_COUNT_TWO

    failed_rec = next(
        i for i in eval_stage.items if i['criterion_id'] == 'branch_broken'
    )
    assert failed_rec['status'] == ProcessingStatus.FAILED
    assert 'Invalid JSON schema' in failed_rec['error_message']


def test_format_context_formatting():
    chunk1 = Document(
        page_content='SECTION: Juridica\n\nTexto do chunk 1',
        metadata={
            'chunk_id': 'c1',
            'chunk_index': 0,
            'section_title': 'Juridica',
        },
    )
    chunk2 = Document(
        page_content='Texto do chunk 2',
        metadata={
            'chunk_id': 'c2',
            'chunk_index': 1,
            'section_title': 'Juridica',
        },
    )
    res_list = format_context([chunk1, chunk2])
    assert '## CONTEXTO DA SEÇÃO: Juridica' in res_list
    assert '[FONTE] chunk_id: c1\nTexto do chunk 1' in res_list
    assert '[FONTE] chunk_id: c2\nTexto do chunk 2' in res_list

    res_dict = format_context({'evidence_chunks': [chunk1, chunk2]})
    assert res_dict == res_list


@pytest.mark.asyncio
async def test_retrieve_evaluation_payloads_structure():
    now = '2026-09-14T00:00:00'
    typ_id = str(uuid4())
    tax_id = str(uuid4())
    tree = [
        {
            'id': typ_id,
            'name': 'Tipificacao 1',
            'sources': [],
            'created_at': now,
            'taxonomies': [
                {
                    'id': tax_id,
                    'typification_id': typ_id,
                    'title': 'Habilitacao Juridica',
                    'description': 'Desc Tax',
                    'created_at': now,
                    'sources': [
                        {
                            'id': str(uuid4()),
                            'name': 'Edital',
                            'description': 'Ref',
                            'created_at': now,
                        }
                    ],
                    'branches': [
                        {
                            'id': str(uuid4()),
                            'taxonomy_id': tax_id,
                            'title': 'Contrato Social',
                            'description': 'Apresentar contrato ativo.',
                            'created_at': now,
                        }
                    ],
                }
            ],
        }
    ]

    mock_vstore = MagicMock()
    mock_vstore.asimilarity_search = AsyncMock(
        return_value=[
            Document(
                page_content='Contrato social regular.',
                metadata={
                    'chunk_id': 'chunk_1',
                    'chunk_index': 1,
                    'source': 'lumina/storage/uploads/doc.pdf',
                    'section_title': 'Habilitacao Juridica',
                },
            )
        ]
    )
    db_release = MagicMock()
    db_release.file_path = 'uploads/doc.pdf'

    payloads = await retrieve_evaluation_payloads(
        mock_vstore, tree, db_release
    )

    assert len(payloads) == 1
    p = payloads[0]
    assert p['expected_section'] == 'Habilitacao Juridica'
    assert p['source'] == 'Edital'
    assert 'Contrato Social' in p['requirement']
    assert '[FONTE] chunk_id: chunk_1' in p['document']
    assert len(p['_chunks']) == 1
    assert p['retrieved_chunks'] == ['chunk_1']
