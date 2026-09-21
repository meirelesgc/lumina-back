# ruff: noqa: PLR2004
from lumina.services.ai.stages.section_models import Heading
from lumina.services.ai.stages.sections import (
    clean_markup,
    make_adjacent_merger,
    make_orphan_cleaner,
    make_repeated_cleaner,
    reclassify_numbering_level,
    run_heading_pipeline,
    strip_markup,
)


def test_strip_markup():
    assert strip_markup('**Título em Negrito**') == 'Título em Negrito'
    assert strip_markup('<u>Sublinhado</u>') == 'Sublinhado'
    assert (
        strip_markup('<mark>Destaque</mark> com *itálico*')
        == 'Destaque com itálico'
    )


def test_clean_markup():
    headings = [
        Heading(
            line_number=1,
            level=1,
            title='**1. INTRODUÇÃO**',
            raw='# **1. INTRODUÇÃO**',
        ),
        Heading(
            line_number=5,
            level=2,
            title='<u>1.1 Detalhes</u>',
            raw='## <u>1.1 Detalhes</u>',
        ),
    ]
    cleaned = clean_markup(headings, '')
    assert cleaned[0].title == '1. INTRODUÇÃO'
    assert cleaned[1].title == '1.1 Detalhes'


def test_make_repeated_cleaner():
    cleaner = make_repeated_cleaner(min_occurrences=3)
    headings = [
        Heading(
            line_number=1,
            level=1,
            title='Secretaria Municipal',
            raw='# Secretaria Municipal',
        ),
        Heading(
            line_number=20,
            level=1,
            title='Secretaria Municipal',
            raw='# Secretaria Municipal',
        ),
        Heading(
            line_number=40,
            level=1,
            title='Secretaria Municipal',
            raw='# Secretaria Municipal',
        ),
        Heading(
            line_number=10,
            level=2,
            title='Objeto do Edital',
            raw='## Objeto do Edital',
        ),
    ]
    filtered = cleaner(headings, '')
    assert len(filtered) == 1
    assert filtered[0].title == 'Objeto do Edital'


def test_make_adjacent_merger():
    full_text = """
#### 1.0. DO OBJETO:

#### CONTRATAÇÃO DE EMPRESA ESPECIALIZADA EM AQUISIÇÃO DE MATERIAL

Compõem este Edital os seguintes anexos com mais de vinte caracteres.
"""
    headings = [
        Heading(
            line_number=2,
            level=4,
            title='1.0. DO OBJETO:',
            raw='#### 1.0. DO OBJETO:',
        ),
        Heading(
            line_number=4,
            level=4,
            title=(
                'CONTRATAÇÃO DE EMPRESA ESPECIALIZADA EM AQUISIÇÃO DE MATERIAL'
            ),
            raw=(
                '#### CONTRATAÇÃO DE EMPRESA ESPECIALIZADA EM AQUISIÇÃO DE'
                ' MATERIAL'
            ),
        ),
    ]
    merger = make_adjacent_merger(max_gap_chars=5)
    merged = merger(headings, full_text)
    assert len(merged) == 1
    assert (
        merged[0].title
        == '1.0. DO OBJETO: CONTRATAÇÃO DE EMPRESA ESPECIALIZADA EM'
        ' AQUISIÇÃO DE MATERIAL'
    )
    assert merged[0].line_number == 2


def test_reclassify_numbering_level():
    headings = [
        Heading(
            line_number=1,
            level=4,
            title='1.0. DO OBJETO:',
            raw='#### 1.0. DO OBJETO:',
        ),
        Heading(
            line_number=5,
            level=4,
            title='1.1 ESPECIFICAÇÕES',
            raw='#### 1.1 ESPECIFICAÇÕES',
        ),
        Heading(
            line_number=10,
            level=4,
            title='1.1.1 Detalhe Técnico',
            raw='#### 1.1.1 Detalhe Técnico',
        ),
        Heading(
            line_number=15,
            level=6,
            title='CLÁUSULA II – DO PREÇO',
            raw='###### CLÁUSULA II – DO PREÇO',
        ),
        Heading(
            line_number=20,
            level=4,
            title='ANEXO IV - TERMO',
            raw='#### ANEXO IV - TERMO',
        ),
        Heading(
            line_number=25,
            level=2,
            title='Justificativa Sem Número',
            raw='## Justificativa Sem Número',
        ),
    ]
    reclassified = reclassify_numbering_level(headings, '')
    assert reclassified[0].level == 1
    assert reclassified[0].level_source == 'numbering_pattern'

    assert reclassified[1].level == 2
    assert reclassified[1].level_source == 'numbering_pattern'

    assert reclassified[2].level == 3
    assert reclassified[2].level_source == 'numbering_pattern'

    assert reclassified[3].level == 1
    assert reclassified[3].level_source == 'numbering_pattern'

    assert reclassified[4].level == 1
    assert reclassified[4].level_source == 'numbering_pattern'

    assert reclassified[5].level == 2
    assert reclassified[5].level_source == 'font'


def test_orphan_cleaner_keeps_headings_with_content():
    full_text = """
# 1. Introdução
Este é um texto com mais de vinte caracteres para garantir a permanência.

# 2. Conclusão
Fim.
"""
    headings = [
        Heading(
            line_number=2,
            level=1,
            title='1. Introdução',
            raw='# 1. Introdução',
        ),
        Heading(
            line_number=5,
            level=1,
            title='2. Conclusão',
            raw='# 2. Conclusão',
        ),
    ]
    cleaner = make_orphan_cleaner(min_chars=20)
    filtered = cleaner(headings, full_text)
    assert len(filtered) == 1
    assert filtered[0].title == '1. Introdução'


def test_run_heading_pipeline_full_integration():
    full_text = """
# **Cabeçalho Repetido**
# **Cabeçalho Repetido**
# **Cabeçalho Repetido**

#### 1.0. DO OBJETO:
#### AQUISIÇÃO DE MEDICAMENTOS

Texto com mais de trinta caracteres informando os requisitos.
"""
    headings = [
        Heading(
            line_number=2,
            level=1,
            title='**Cabeçalho Repetido**',
            raw='# **Cabeçalho Repetido**',
        ),
        Heading(
            line_number=3,
            level=1,
            title='**Cabeçalho Repetido**',
            raw='# **Cabeçalho Repetido**',
        ),
        Heading(
            line_number=4,
            level=1,
            title='**Cabeçalho Repetido**',
            raw='# **Cabeçalho Repetido**',
        ),
        Heading(
            line_number=6,
            level=4,
            title='1.0. DO OBJETO:',
            raw='#### 1.0. DO OBJETO:',
        ),
        Heading(
            line_number=7,
            level=4,
            title='AQUISIÇÃO DE MEDICAMENTOS',
            raw='#### AQUISIÇÃO DE MEDICAMENTOS',
        ),
    ]
    res = run_heading_pipeline(headings, full_text)
    assert len(res) == 1
    assert res[0].title == '1.0. DO OBJETO: AQUISIÇÃO DE MEDICAMENTOS'
    assert res[0].level == 1
    assert res[0].level_source == 'numbering_pattern'
