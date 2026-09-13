from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from langchain_core.documents import Document

from lumina.schemas.processing_run import ProcessingStatus
from lumina.services.ai.stages.evaluation import (
    evaluate_criteria_batch as apply_tree,
)
from lumina.services.ai.stages.retrieval import get_expanded_chunks
from lumina.services.ai.stages.synthesis import partition_synthesis_text
from lumina.services.run_logger import RunLogger

EXPECTED_SCORE_NINE = 9
EXPECTED_REFS_COUNT_ONE = 1
EXPECTED_ITEMS_COUNT_TWO = 2
EXPECTED_EXPANDED_COUNT = 3


@pytest.mark.asyncio
async def test_get_expanded_chunks_empty():
    mock_vstore = MagicMock()
    result = await get_expanded_chunks(mock_vstore, [])
    assert result == []


@pytest.mark.asyncio
async def test_get_expanded_chunks_missing_metadata():
    mock_vstore = MagicMock()
    chunk_no_meta = Document(page_content='Sem metadata', metadata={})
    result = await get_expanded_chunks(mock_vstore, [chunk_no_meta])
    assert result == []


@pytest.mark.asyncio
async def test_get_expanded_chunks_with_direct_sql():
    # Simula PGVector com _make_async_session e EmbeddingStore
    mock_vstore = MagicMock()
    mock_session = AsyncMock()

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_session
    mock_ctx.__aexit__.return_value = None
    mock_vstore._make_async_session.return_value = mock_ctx

    mock_collection = MagicMock()
    mock_collection.uuid = 'mock-uuid'
    mock_vstore.aget_collection = AsyncMock(return_value=mock_collection)

    from langchain_postgres.vectorstores import (  # noqa: PLC0415
        _get_embedding_collection_store,  # noqa: PLC2701
    )

    EmbeddingStore, _ = _get_embedding_collection_store(None)
    mock_vstore.EmbeddingStore = EmbeddingStore

    record1 = MagicMock(
        id=1,
        document='Texto chunk 0',
        cmetadata={'source': 'doc1', 'chunk_index': 0},
    )
    record2 = MagicMock(
        id=2,
        document='Texto chunk 1',
        cmetadata={'source': 'doc1', 'chunk_index': 1},
    )
    record3 = MagicMock(
        id=3,
        document='Texto chunk 2',
        cmetadata={'source': 'doc1', 'chunk_index': 2},
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        record1,
        record2,
        record3,
    ]
    mock_session.execute = AsyncMock(return_value=mock_result)

    original = [
        Document(
            page_content='Texto chunk 1',
            metadata={'source': 'doc1', 'chunk_index': 1},
        )
    ]

    expanded = await get_expanded_chunks(mock_vstore, original)

    assert len(expanded) == EXPECTED_EXPANDED_COUNT
    assert [c.metadata['chunk_index'] for c in expanded] == [0, 1, 2]
    assert not mock_vstore.asimilarity_search.called


@pytest.mark.asyncio
async def test_get_expanded_chunks_fallback():
    # Quando não há _make_async_session, usa o fallback asimilarity_search
    mock_vstore = MagicMock(spec=['asimilarity_search'])
    fallback_doc = Document(
        page_content='Fallback text',
        metadata={'source': 'doc1', 'chunk_index': 0},
    )
    mock_vstore.asimilarity_search = AsyncMock(return_value=[fallback_doc])

    original = [
        Document(
            page_content='Texto chunk 0',
            metadata={'source': 'doc1', 'chunk_index': 0},
        )
    ]

    expanded = await get_expanded_chunks(mock_vstore, original)
    assert len(expanded) == 1
    assert mock_vstore.asimilarity_search.called


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
        page_content='Texto do resumo',
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
            'expected_session': 'Resumo',
            'query': 'Analise o item',
            '_sessions': [mock_chunk],
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
            'expected_session': 'Sessao 1',
            'query': 'query 1',
            '_sessions': [valid_chunk],
        },
        {
            'id': 'branch_broken',
            'document': 'doc 2',
            'source': 'fonte',
            'requirement': 'req 2',
            'expected_session': 'Sessao 2',
            'query': 'query 2',
            '_sessions': [],
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
