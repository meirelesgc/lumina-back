"""
Jornada: o proponente envia o anteprojeto e espera que o nome dele não
chegue ao provedor de embeddings nem ao LLM de avaliação. O texto enviado
é o dos chunks anonimizados, então estes testes verificam a anonimização
contra os `person_names` dos gabaritos de `tests/fixtures/documents/`
(OpenSpec: anonymize-person-names).

Nome de autoria sem anonimização é falha crítica: tolerância zero, por
documento.
"""

import pytest

from tests.fixtures.answer_keys import (
    SECTIONS_KEYS,
    anonymized,
    doc_id,
    normalize,
    pdf_for,
    person_names,
)

FIELDS = ('page_content', 'section_title', 'section_path')


def field_text(chunk, field: str) -> str:
    if field == 'page_content':
        return normalize(chunk.page_content)
    return normalize(chunk.metadata[field])


@pytest.mark.parametrize('answer_key', SECTIONS_KEYS, ids=doc_id)
def test_nenhum_chunk_anonimizado_traz_nome_de_autoria(answer_key):
    names = person_names(answer_key)
    assert names, 'Gabarito sem person_names'

    leaks = [
        f'{chunk.metadata["chunk_id"]}.{field}: {name}'
        for chunk in anonymized(pdf_for(answer_key))
        for field in FIELDS
        for name in names
        if normalize(name) in field_text(chunk, field)
    ]

    assert not leaks, 'Nomes sem anonimização:\n' + '\n'.join(leaks)
