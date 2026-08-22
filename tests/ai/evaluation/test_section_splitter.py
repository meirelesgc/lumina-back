import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain_community.document_loaders import PyMuPDFLoader

from lumina.core.llm import get_model
from lumina.services.vector_service import (
    ChunkSections,
    SectionInfo,
    _split_by_sections,
)

DATASETS_DIR = Path(__file__).parent / 'datasets' / 'validation_docs'
GROUND_TRUTH_PATH = DATASETS_DIR / 'ground_truth_sections.json'


def load_ground_truth():
    with open(GROUND_TRUTH_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_split_by_sections_with_ground_truth():
    """
    Testa deterministicamente a função `_split_by_sections` utilizando
    um mock estruturado e o gabarito definido em `ground_truth_sections.json`.
    """
    gt_data = load_ground_truth()
    target_gt = next(
        item
        for item in gt_data
        if item['document_path'] == 'conclusao_referencias.pdf'
    )
    expected_sections = target_gt['expected_sections']

    pdf_path = DATASETS_DIR / target_gt['document_path']
    assert pdf_path.exists(), f'Arquivo PDF não encontrado: {pdf_path}'

    loader = PyMuPDFLoader(str(pdf_path), mode='single')
    documents = loader.load()
    assert len(documents) > 0, (
        'O documento PDF deve carregar ao menos 1 página'
    )

    mock_model = MagicMock()
    mock_structured_model = MagicMock()

    mock_structured_model.invoke.side_effect = [
        ChunkSections(
            sections=[
                SectionInfo(
                    section_name='Considerações finais',
                    start_text='1 Considerações finais Este artigo apresentou um novo processo de mediação de modelagem',
                    end_text='desenvolver um SRC que evolua de forma dinâmica à medida que o modelo seja alterado.',
                ),
            ]
        ),
        ChunkSections(
            sections=[
                SectionInfo(
                    section_name='Referências',
                    start_text='Referências BAADER, F.; KOWALCZYK, P.; TISCHENDORF, J. Description logics in the era of knowledge',
                    end_text=None,
                ),
            ]
        ),
        ChunkSections(sections=[]),
    ]
    mock_model.with_structured_output.return_value = mock_structured_model

    split_documents = _split_by_sections(documents, mock_model)

    assert len(split_documents) == len(expected_sections), (
        f'Esperado {len(expected_sections)} seções, mas obtido {len(split_documents)}'
    )

    retrieved_section_titles = [
        doc.metadata.get('section_title') for doc in split_documents
    ]

    for expected in expected_sections:
        assert expected in retrieved_section_titles, (
            f"A seção '{expected}' definida no Ground Truth não foi recuperada."
        )

    cons_doc = next(
        doc
        for doc in split_documents
        if doc.metadata.get('section_title') == 'Considerações finais'
    )
    assert 'Considerações finais' in cons_doc.page_content
    assert 'mediação de modelagem' in cons_doc.page_content

    ref_doc = next(
        doc
        for doc in split_documents
        if doc.metadata.get('section_title') == 'Referências'
    )
    assert 'Referências' in ref_doc.page_content


@pytest.mark.ai
@pytest.mark.asyncio
async def test_split_by_sections_real_llm_evaluation():
    """
    Teste real de Avaliação de IA: faz chamadas reais ao modelo LLM (LangChain / OpenAI)
    para o arquivo `conclusao_referencias.pdf` e valida se o modelo realmente identifica
    e recupera as seções de Conclusão/Considerações Finais e Referências.
    """
    gt_data = load_ground_truth()
    target_gt = next(
        item
        for item in gt_data
        if item['document_path'] == 'conclusao_referencias.pdf'
    )
    expected_sections = target_gt['expected_sections']

    pdf_path = DATASETS_DIR / target_gt['document_path']
    loader = PyMuPDFLoader(str(pdf_path), mode='single')
    documents = loader.load()

    # Obtém o modelo real configurado na aplicação
    real_model = await get_model()

    # Executa a função chamando o modelo LLM real
    split_documents = _split_by_sections(documents, real_model)

    assert len(split_documents) >= len(expected_sections), (
        f'O modelo real retornou {len(split_documents)} seções, esperava pelo menos {len(expected_sections)}.'
    )

    retrieved_section_titles = [
        (doc.metadata.get('section_title') or '').lower()
        for doc in split_documents
    ]

    # Valida se cada seção esperada do Ground Truth foi encontrada (case-insensitive)
    for expected in expected_sections:
        assert any(
            expected.lower() in title for title in retrieved_section_titles
        ), (
            f"O modelo LLM real não conseguiu recuperar a seção '{expected}'. Seções obtidas: {retrieved_section_titles}"
        )

    # Garante que cada documento recuperado pela LLM real tem conteúdo válido
    for doc in split_documents:
        assert len(doc.page_content.strip()) > 0
