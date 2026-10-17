"""
Com `DEBUG_INGESTION_AUDIT=True`, a avaliação grava o sumário do documento e,
para cada critério, a seleção de seções, o contexto enviado ao avaliador e o
veredito, para depurar por que um critério recebeu aquele parecer
(OpenSpec: outline-section-selection).
"""

import pytest
from langchain_core.documents import Document

from lumina.services.ai.stages import audit
from lumina.services.ai.stages.outline import build_outline, outline_markdown

SOURCE = 'lumina/storage/uploads/anteprojeto.pdf'


@pytest.fixture
def outline():
    return build_outline([
        Document(
            page_content='[1. Introdução] Texto da introdução.',
            metadata={
                'section_index': 0,
                'section_title': '1. Introdução',
                'section_path': '1. Introdução',
                'page': 0,
                'chunk_index_in_section': 0,
                'chunk_id': 'chunk_0_0',
            },
        )
    ])


@pytest.fixture
def payloads():
    return [
        {
            'id': 'objetivo-geral',
            'requirement': 'Objetivo geral: está definido?',
            'document': '[FONTE] chunk_id: chunk_0_0\nTexto da introdução.',
            'fulfilled': True,
            'score': 8,
            'feedback': '**Veredito:** Atende.',
            'context_selection': {
                'scope': 'SPECIFIC_SECTION',
                'outcome': 'selected',
                'section_ids': ['s01'],
                'rounds': [
                    {
                        'requested': ['s01'],
                        'invalid': [],
                        'reason': 'A introdução traz o objetivo.',
                        'enough': False,
                        'not_found': False,
                    }
                ],
                'tokens': 5,
                'model': 'gpt-6-luna',
                'error': None,
            },
        }
    ]


def test_com_a_flag_grava_sumario_e_selecao(
    tmp_path, monkeypatch, outline, payloads
):
    monkeypatch.setattr(audit.SETTINGS, 'DEBUG_INGESTION_AUDIT', True)

    audit.export_selection_audit(SOURCE, outline, payloads, tmp_path)

    outline_file = tmp_path / '05_outline' / 'anteprojeto.md'
    selection_file = (
        tmp_path / '06_selection' / 'anteprojeto' / 'objetivo-geral.md'
    )
    assert outline_markdown(outline) in outline_file.read_text(
        encoding='utf-8'
    )
    text = selection_file.read_text(encoding='utf-8')
    assert 'A introdução traz o objetivo.' in text
    assert '[FONTE] chunk_id: chunk_0_0' in text
    assert '**Veredito:** Atende.' in text


def test_sem_a_flag_nao_grava_nada(tmp_path, monkeypatch, outline, payloads):
    monkeypatch.setattr(audit.SETTINGS, 'DEBUG_INGESTION_AUDIT', False)

    audit.export_selection_audit(SOURCE, outline, payloads, tmp_path)

    assert not any(tmp_path.iterdir())
