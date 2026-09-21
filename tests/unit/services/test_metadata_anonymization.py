import pytest
from langchain_core.documents import Document

from lumina.services.ai.stages.anonymization import anonymize_chunks


@pytest.mark.asyncio
async def test_metadata_anonymization_cpf_and_names():
    """
    Garante que Presidio mascara dados sensiveis (CPF, nomes) presentes em
    section_title e section_path nos metadados, alem do page_content.
    """
    chunk = Document(
        page_content='O servidor CPF 123.456.789-00 assinou o documento.',
        metadata={
            'chunk_id': 'chunk_0_0',
            'section_title': 'Parecer do CPF 123.456.789-00',
            'section_path': 'Edital > Parecer do CPF 123.456.789-00',
        },
    )

    anonymized = await anonymize_chunks([chunk])

    assert len(anonymized) == 1
    doc = anonymized[0]

    # Verifica page_content anonimizado
    assert '123.456.789-00' not in doc.page_content
    assert '<CPF_' in doc.page_content

    # Verifica section_title e section_path anonimizados nos metadados
    assert '123.456.789-00' not in doc.metadata['section_title']
    assert '<CPF_' in doc.metadata['section_title']

    assert '123.456.789-00' not in doc.metadata['section_path']
    assert '<CPF_' in doc.metadata['section_path']
