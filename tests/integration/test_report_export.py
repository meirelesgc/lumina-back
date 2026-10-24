"""
Jornada: o analista avalia um edital e baixa o relatório da release em PDF.
A síntese e os pareceres chegam do modelo em Markdown. O relatório deve
mostrar o conteúdo formatado, sem marcadores crus, com a identidade visual
do LUMINA. Releases antigas em texto puro continuam legíveis. O mesmo vale
para o relatório da base de conhecimento (tipificações).

O PDF é lido com o PyMuPDF, que devolve o texto e as fontes de cada página
(OpenSpec: styled-pdf-export).
"""

from http import HTTPStatus

import pymupdf
import pytest

from lumina.models import (
    AppliedBranch,
    AppliedTaxonomy,
    AppliedTypification,
    Document,
    DocumentHistory,
    DocumentRelease,
)
from lumina.schemas.document import DocumentProcessingStatus
from tests.factories.branch_factory import (
    BranchFactory,
    TaxonomyFactory,
    TypificationFactory,
)

SYNTHESIS = (
    '## Visão geral\n\n'
    'O edital **atende** a *maioria* dos critérios.\n\n'
    '- Prazo adequado\n'
    '- Orçamento < R$ 10 mil & sem reserva\n\n'
    '| Critério | Nota |\n'
    '| --- | --- |\n'
    '| Prazo | 9 |'
)
FEEDBACK = '**Veredito:** Atende.\n\n1. Cronograma presente\n2. Metas claras'
LEGACY = 'Linha antiga um\nLinha antiga dois'
DOCUMENT_NAME = 'Edital de Pesquisa 2026'


async def persist(session, *entities):
    for entity in entities:
        session.add(entity)
    await session.commit()
    for entity in entities:
        await session.refresh(entity)


async def evaluated_release(session, description, feedback):
    document = Document(
        name=DOCUMENT_NAME,
        identifier='ED-2026',
        description='Edital de fomento',
        processing_status=DocumentProcessingStatus.IDLE,
    )
    await persist(session, document)
    history = DocumentHistory(document_id=document.id, status='ACTIVE')
    await persist(session, history)
    release = DocumentRelease(
        history_id=history.id,
        file_path='edital.pdf',
        version='v1',
        description=description,
    )
    await persist(session, release)
    typification = AppliedTypification(
        name='Edital de fomento', applied_release_id=release.id
    )
    await persist(session, typification)
    taxonomy = AppliedTaxonomy(
        title='Planejamento',
        applied_typification_id=typification.id,
        description='Critérios de planejamento',
    )
    await persist(session, taxonomy)
    branch = AppliedBranch(
        title='Cronograma',
        applied_taxonomy_id=taxonomy.id,
        description='O edital apresenta cronograma',
        feedback=feedback,
        fulfilled=True,
        score=9,
    )
    await persist(session, branch)
    ids = document.id, release.id
    # A rota usa a mesma sessão: descarta a árvore em cache, montada antes
    # dos filhos existirem.
    session.expire_all()
    return ids


def read_pdf(response):
    assert response.status_code == HTTPStatus.OK
    assert response.headers['content-type'] == 'application/pdf'
    with pymupdf.open(stream=response.content, filetype='pdf') as pdf:
        text = ''.join(page.get_text() for page in pdf)
        fonts = {font[3] for page in pdf for font in page.get_fonts(full=True)}
    return text, fonts


def assert_lumina_identity(text, fonts):
    assert any('Barlow' in font for font in fonts)
    assert any('Lexend' in font for font in fonts)
    assert 'lumina.fiocruz.br' in text


def assert_markdown_rendered(text):
    for marker in ('**', '## ', '| ', '- Prazo', '---'):
        assert marker not in text
    assert 'Visão geral' in text
    assert 'atende' in text
    assert 'Orçamento < R$ 10 mil & sem reserva' in text
    assert 'Veredito:' in text
    assert 'Metas claras' in text


@pytest.mark.asyncio
async def test_analista_baixa_relatorio_da_release_formatado(client, session):
    _, release_id = await evaluated_release(session, SYNTHESIS, FEEDBACK)

    # 1. O analista pede o PDF pela rota de exportação de relatórios
    text, fonts = read_pdf(
        client.get(
            '/export/release/pdf',
            params={'document_release_id': str(release_id)},
        )
    )

    # 2. A capa traz o documento e o relatório segue a identidade do LUMINA
    assert DOCUMENT_NAME in text
    assert_lumina_identity(text, fonts)

    # 3. Síntese e parecer aparecem formatados, sem marcadores crus
    assert_markdown_rendered(text)
    assert 'Cronograma' in text
    assert 'Cumprido' in text


@pytest.mark.asyncio
async def test_analista_baixa_relatorio_pela_rota_do_documento(
    client, session
):
    document_id, release_id = await evaluated_release(
        session, SYNTHESIS, FEEDBACK
    )

    text, fonts = read_pdf(
        client.get(f'/doc/{document_id}/release/{release_id}/export/pdf')
    )

    assert_lumina_identity(text, fonts)
    assert_markdown_rendered(text)


@pytest.mark.asyncio
async def test_release_antiga_em_texto_puro_continua_legivel(client, session):
    _, release_id = await evaluated_release(
        session, LEGACY, 'Parecer simples.'
    )

    text, _ = read_pdf(
        client.get(
            '/export/release/pdf',
            params={'document_release_id': str(release_id)},
        )
    )

    assert 'Linha antiga um\nLinha antiga dois' in text
    assert 'Parecer simples.' in text


@pytest.mark.asyncio
async def test_release_sem_sintese_gera_pdf(client, session):
    _, release_id = await evaluated_release(session, None, FEEDBACK)

    text, _ = read_pdf(
        client.get(
            '/export/release/pdf',
            params={'document_release_id': str(release_id)},
        )
    )

    assert 'Cronograma' in text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'path', ['/export/typifications/pdf', '/typification/export/pdf']
)
async def test_analista_baixa_relatorio_da_base_de_conhecimento(
    client, session, user, path
):
    typification = TypificationFactory(name='Tipificação <ETP> & afins')
    typification.set_creation_audit(user.id)
    await persist(session, typification)
    taxonomy = TaxonomyFactory(typification_id=typification.id)
    taxonomy.set_creation_audit(user.id)
    await persist(session, taxonomy)
    branch = BranchFactory(
        taxonomy_id=taxonomy.id,
        title='Justificativa',
        description='Exige **justificativa** da contratação',
    )
    branch.set_creation_audit(user.id)
    await persist(session, branch)
    typification_id = typification.id
    session.expire_all()

    text, fonts = read_pdf(
        client.get(path, params={'typification_id': str(typification_id)})
    )

    assert_lumina_identity(text, fonts)
    assert 'Tipificação <ETP> & afins' in text
    assert 'Justificativa' in text
    assert '**' not in text
