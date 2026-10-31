from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.documents import Document

from lumina.services.ai.stages import retrieval
from lumina.services.ai.stages.evaluation import (
    evaluate_criteria_batch as apply_tree,
)
from lumina.services.ai.stages.retrieval import (
    format_context,
    get_base_filter,
    reciprocal_rank_fusion,
)

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


@pytest.mark.asyncio
async def test_apply_tree_isolates_schema_validation_error():
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

    result = await apply_tree(mock_chain, eval_args)

    assert len(result) == EXPECTED_ITEMS_COUNT_TWO
    ok_item = next(r for r in result if r['id'] == 'branch_ok')
    assert ok_item['score'] == EXPECTED_SCORE_NINE
    assert ok_item['fulfilled'] is True
    assert len(ok_item['references']) == EXPECTED_REFS_COUNT_ONE

    broken_item = next(r for r in result if r['id'] == 'branch_broken')
    assert broken_item['fulfilled'] is False
    assert 'Erro na validação de schema' in broken_item['feedback']


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


def test_reciprocal_rank_fusion_single_list_matches_topk():
    docs = [
        Document(page_content='a', metadata={'chunk_id': 'c1'}),
        Document(page_content='b', metadata={'chunk_id': 'c2'}),
        Document(page_content='c', metadata={'chunk_id': 'c3'}),
    ]

    fused = reciprocal_rank_fusion([docs], top_n=2)

    assert [d.metadata['chunk_id'] for d in fused] == ['c1', 'c2']


def test_reciprocal_rank_fusion_merges_and_deduplicates():
    list_a = [
        Document(page_content='a', metadata={'chunk_id': 'c1'}),
        Document(page_content='b', metadata={'chunk_id': 'c2'}),
    ]
    list_b = [
        Document(page_content='c', metadata={'chunk_id': 'c2'}),
        Document(page_content='d', metadata={'chunk_id': 'c3'}),
    ]

    fused = reciprocal_rank_fusion([list_a, list_b], top_n=5)
    ids = [d.metadata['chunk_id'] for d in fused]

    assert sorted(ids) == ['c1', 'c2', 'c3']
    # c2 aparece em 1o lugar em ambas as listas, deve liderar a fusao
    assert ids[0] == 'c2'


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
def test_get_base_filter_isolates_the_document():
    db_release = MagicMock()
    db_release.file_path = 'uploads/doc.pdf'

    assert get_base_filter(db_release) == {
        'source': 'lumina/storage/uploads/doc.pdf'
    }


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
def test_contextos_marcam_as_frases_do_chunk():
    chunk = Document(
        page_content='[Método] Primeira frase. Segunda frase.',
        metadata={
            'chunk_id': 'chunk_0_0',
            'section_title': 'Método',
            'sentences': [
                {'n': 1, 'start': 9, 'end': 24, 'rects': []},
                {'n': 2, 'start': 25, 'end': 39, 'rects': []},
            ],
        },
    )

    assert '[s1] Primeira frase. [s2] Segunda frase.' in (
        retrieval.format_context([chunk])
    )
    assert '[s1] Primeira frase. [s2] Segunda frase.' in (
        retrieval.build_chunk_prompts([chunk])[0]
    )


def test_contextos_nao_marcam_chunk_indexado_antes_das_frases():
    chunk = Document(
        page_content='[Método] Primeira frase. Segunda frase.',
        metadata={'chunk_id': 'chunk_0_0', 'section_title': 'Método'},
    )

    assert '[s1]' not in retrieval.format_context([chunk])
    assert '[s1]' not in retrieval.build_chunk_prompts([chunk])[0]
