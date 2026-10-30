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


def chunk(text: str, role: str = 'unknown', title: str = 'Corpo') -> Document:
    return Document(
        page_content=text,
        metadata={
            'chunk_id': 'chunk_0_0',
            'section_title': title,
            'section_path': title,
            'section_role': role,
        },
    )


@pytest.mark.asyncio
async def test_nome_em_maiusculas_e_mascarado_no_texto_e_nos_titulos():
    doc = chunk(
        'UNIVERSIDADE DO ESTADO\n\nMARIANA SOUZA LIMA\n\n'
        'Estratégias de teste de software.',
        title='UNIVERSIDADE DO ESTADO MARIANA SOUZA LIMA',
    )

    [anonymized] = await anonymize_chunks([doc])

    assert 'MARIANA' not in anonymized.page_content
    assert '<PERSON_0>' in anonymized.page_content
    assert 'MARIANA' not in anonymized.metadata['section_title']
    assert '<PERSON_0>' in anonymized.metadata['section_title']
    assert 'MARIANA' not in anonymized.metadata['section_path']


@pytest.mark.asyncio
async def test_mesmo_nome_em_duas_caixas_recebe_um_marcador():
    chunks = [
        chunk('Autora: MARIANA SOUZA LIMA\n\nOrientador: Paulo Ricardo Nunes'),
        chunk('O trabalho de Mariana Souza Lima discute testes.'),
    ]

    anonymized = await anonymize_chunks(chunks)

    assert 'Mariana' not in anonymized[1].page_content
    marker = anonymized[1].page_content.split()[3]
    assert marker.startswith('<PERSON_')
    assert marker in anonymized[0].page_content
    mapping = anonymized[-1].metadata['presidio_mapping']['PERSON']
    assert list(mapping.values()).count(marker) == 1


@pytest.mark.asyncio
async def test_nome_de_autoria_e_mascarado_nas_referencias():
    chunks = [
        chunk('Trabalho apresentado por Mariana Souza Lima ao colegiado.'),
        chunk(
            'LIMA, Mariana Souza. Testes com LLM. 2025.\n'
            'Mariana Souza Lima. Avaliação humana. 2024.',
            role='references',
            title='Referências',
        ),
    ]

    anonymized = await anonymize_chunks(chunks)

    assert 'Mariana Souza Lima' not in anonymized[1].page_content


@pytest.mark.asyncio
async def test_autor_so_das_referencias_continua_visivel():
    chunks = [
        chunk('O trabalho discute avaliação de modelos de linguagem.'),
        chunk(
            'Segundo Bruno Carlos Ferreira, a avaliação exige especialistas.',
            role='references',
            title='Referências',
        ),
    ]

    anonymized = await anonymize_chunks(chunks)

    assert 'Bruno Carlos Ferreira' in anonymized[1].page_content


@pytest.mark.asyncio
async def test_sobrenome_de_citacao_continua_visivel():
    doc = chunk('Laubheimer (2020) propõe heurísticas de usabilidade.')

    [anonymized] = await anonymize_chunks([doc])

    assert 'Laubheimer' in anonymized.page_content


@pytest.mark.asyncio
async def test_expressao_com_palavras_em_minusculas_no_documento_continua():
    chunks = [
        chunk('A Bahia lidera a geração de Energias Renováveis no país.'),
        chunk('O mapa das energias renováveis cobre usinas eólicas.'),
    ]

    anonymized = await anonymize_chunks(chunks)

    assert 'Energias Renováveis' in anonymized[0].page_content


@pytest.mark.asyncio
async def test_expressao_igual_a_titulo_de_secao_continua():
    doc = chunk(
        '[3 APLICAÇÕES CORRELATADAS] Em seu estudo Coelho Júnior',
        title='3 APLICAÇÕES CORRELATADAS',
    )

    [anonymized] = await anonymize_chunks([doc])

    assert 'APLICAÇÕES CORRELATADAS' in anonymized.page_content
    assert anonymized.metadata['section_title'] == '3 APLICAÇÕES CORRELATADAS'


def chunk_com_frases(text: str, sentences: list[dict]) -> Document:
    return Document(
        page_content=text,
        metadata={
            'chunk_id': 'chunk_0_0',
            'section_title': 'Corpo',
            'section_path': 'Corpo',
            'sentences': sentences,
        },
    )


@pytest.mark.asyncio
async def test_frases_acompanham_o_texto_anonimizado():
    first = 'O servidor CPF 123.456.789-00 assinou o documento.'
    second = 'O contrato entra em vigor na data da assinatura.'
    text = f'{first} {second}'
    chunk = chunk_com_frases(
        text,
        [
            {'n': 1, 'start': 0, 'end': len(first), 'rects': []},
            {
                'n': 2,
                'start': len(first) + 1,
                'end': len(text),
                'rects': [[1.0, 2.0, 3.0, 4.0]],
            },
        ],
    )

    [doc] = await anonymize_chunks([chunk])

    one, two = doc.metadata['sentences']
    assert doc.page_content[one['start'] : one['end']].startswith(
        'O servidor CPF <CPF_'
    )
    assert doc.page_content[two['start'] : two['end']] == second
    assert two['rects'] == [[1.0, 2.0, 3.0, 4.0]]


@pytest.mark.asyncio
async def test_varias_entidades_mantem_as_frases_no_lugar():
    first = 'CPF 123.456.789-00 e CPF 987.654.321-00 assinaram.'
    second = 'O prazo de validade do documento é de um ano.'
    text = f'{first} {second}'
    chunk = chunk_com_frases(
        text,
        [
            {'n': 1, 'start': 0, 'end': len(first), 'rects': []},
            {'n': 2, 'start': len(first) + 1, 'end': len(text), 'rects': []},
        ],
    )

    [doc] = await anonymize_chunks([chunk])

    _, two = doc.metadata['sentences']
    assert doc.page_content[two['start'] : two['end']] == second


@pytest.mark.asyncio
async def test_metadados_das_frases_nao_guardam_texto():
    text = 'O servidor CPF 123.456.789-00 assinou o documento.'
    chunk = chunk_com_frases(
        text, [{'n': 1, 'start': 0, 'end': len(text), 'rects': []}]
    )

    [doc] = await anonymize_chunks([chunk])

    assert '123.456.789-00' not in str(doc.metadata['sentences'])
