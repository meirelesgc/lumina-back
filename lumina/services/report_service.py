from datetime import datetime
from functools import cache
from html import escape
from http import HTTPStatus
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)
from reportlab.platypus.tableofcontents import TableOfContents
from sqlalchemy import select
from svglib.svglib import svg2rlg

from lumina.models import Document, DocumentRelease
from lumina.schemas.document_release import DocumentReleasePublic
from lumina.utils.markdown_reportlab import (
    markdown_styles,
    markdown_to_flowables,
)

# Tokens de lumina/assets/design-system/DESIGN.md
COR_LARANJA = colors.HexColor('#f8580a')
COR_TEAL = colors.HexColor('#0e90a0')
COR_OURO = colors.HexColor('#d9ae21')
COR_TINTA = colors.HexColor('#2b2b2b')
COR_FUNDO = colors.HexColor('#efefef')
COR_LINHA = colors.HexColor('#d6d6d6')
COR_LARANJA_TEXTO = colors.HexColor('#b04406')
COR_TEAL_TEXTO = colors.HexColor('#0b6970')

ASSETS = Path(__file__).parents[1] / 'assets' / 'design-system' / 'assets'
FONTS = {
    'Barlow-SemiBold': 'barlow-latin-600-normal.ttf',
    'Lexend-Light': 'lexend-latin-300-normal.ttf',
    'Lexend-Regular': 'lexend-latin-400-normal.ttf',
    'Lexend-Bold': 'lexend-latin-700-normal.ttf',
    'Lexend-ExtraBold': 'lexend-latin-800-normal.ttf',
}
SITE = 'lumina.fiocruz.br'

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_TOP = MARGIN_BOTTOM = 20 * mm
MARGIN_LEFT = 34 * mm
MARGIN_RIGHT = 16 * mm
CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
RAIL_X = 10 * mm
RAIL_WIDTH = 11 * mm

STATUS = {True: 'Cumprido', False: 'Não cumprido', None: 'Indefinido'}


def register_fonts():
    registered = pdfmetrics.getRegisteredFontNames()
    for name, file in FONTS.items():
        if name not in registered:
            pdfmetrics.registerFont(TTFont(name, ASSETS / 'fonts' / file))
    # Lexend não tem itálico: a ênfase em itálico usa o peso Regular.
    for bold, italic, font in [
        (0, 0, 'Lexend-Light'),
        (1, 0, 'Lexend-Bold'),
        (0, 1, 'Lexend-Regular'),
        (1, 1, 'Lexend-Bold'),
    ]:
        addMapping('Barlow', bold, italic, 'Barlow-SemiBold')
        addMapping('Lexend', bold, italic, font)


def get_custom_styles():
    register_fonts()
    styles = markdown_styles(
        body_font='Lexend-Light',
        heading_font='Barlow-SemiBold',
        text_color=COR_TINTA,
        heading_color=COR_LARANJA_TEXTO,
        subheading_color=COR_TEAL_TEXTO,
    )
    body = styles['MdBody']

    def add(name, **kwargs):
        styles.add(ParagraphStyle(name=name, parent=body, **kwargs))

    add(
        'SectionLabel',
        fontName='Lexend-ExtraBold',
        fontSize=9,
        textColor=COR_TEAL_TEXTO,
        spaceAfter=2,
    )
    add(
        'SectionTitle',
        fontName='Barlow-SemiBold',
        fontSize=26,
        leading=28,
        textColor=COR_LARANJA,
        spaceAfter=14,
    )
    add(
        'TocTitle',
        fontName='Barlow-SemiBold',
        fontSize=26,
        leading=28,
        textColor=COR_LARANJA,
        spaceAfter=14,
    )
    add('TocEntry', fontSize=11, leading=22)
    add(
        'Title2',
        fontName='Barlow-SemiBold',
        fontSize=16,
        leading=19,
        textColor=COR_LARANJA_TEXTO,
        spaceBefore=12,
        spaceAfter=4,
    )
    add(
        'Title3',
        fontName='Barlow-SemiBold',
        fontSize=12,
        leading=15,
        textColor=COR_TEAL_TEXTO,
        spaceBefore=8,
        spaceAfter=4,
    )
    add('Criterion', fontName='Lexend-Bold', spaceBefore=8, spaceAfter=0)
    add('Meta', fontSize=8.5, leading=12, textColor=COR_TEAL_TEXTO)
    add(
        'CoverKicker', fontName='Lexend-Bold', fontSize=11, textColor=COR_FUNDO
    )
    add(
        'CoverTitle',
        fontName='Barlow-SemiBold',
        fontSize=40,
        leading=42,
        textColor=COR_FUNDO,
    )
    add('CoverSubtitle', fontSize=14, leading=19, textColor=COR_FUNDO)
    add('CoverMeta', fontSize=9, leading=13, textColor=COR_FUNDO)
    return styles


@cache
def svg(relative_path):
    return svg2rlg(str(ASSETS / relative_path))


def draw_svg(canvas, relative_path, x, y, *, width=None, height=None):  # noqa: PLR0913
    drawing = svg(relative_path)
    scale = width / drawing.width if width else height / drawing.height
    canvas.saveState()
    canvas.translate(x, y)
    canvas.scale(scale, scale)
    renderPDF.draw(drawing, canvas, 0, 0)
    canvas.restoreState()
    return drawing.width * scale, drawing.height * scale


def format_date(value):
    if not value:
        return '-'
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.strftime('%d/%m/%Y')


class LuminaDocTemplate(BaseDocTemplate):
    """A4 com capa laranja e páginas internas com o trilho lateral."""

    def __init__(self, filename, cover, rail_title, styles):
        super().__init__(
            filename,
            pagesize=A4,
            title=cover['title'],
            author='LUMINA · Fiocruz',
        )
        self.cover = cover
        self.rail_title = rail_title
        self.styles = styles
        content = Frame(
            MARGIN_LEFT,
            MARGIN_BOTTOM,
            CONTENT_WIDTH,
            PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM,
            id='content',
        )
        self.addPageTemplates([
            PageTemplate(
                'capa',
                [Frame(0, 0, PAGE_WIDTH, PAGE_HEIGHT, id='capa')],
                onPage=self.draw_cover,
            ),
            PageTemplate('interna', [content], onPage=self.draw_inner),
        ])

    def afterFlowable(self, flowable):
        if (
            isinstance(flowable, Paragraph)
            and flowable.style.name == 'SectionTitle'
        ):
            self.notify(
                'TOCEntry', (0, escape(flowable.getPlainText()), self.page)
            )

    def draw_cover(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(COR_LARANJA)
        canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)
        grid_height = PAGE_HEIGHT
        grid = svg('elements/grade-cruz-capa.svg')
        grid_width = grid.width * grid_height / grid.height
        draw_svg(
            canvas,
            'elements/grade-cruz-capa.svg',
            PAGE_WIDTH - grid_width,
            0,
            height=grid_height,
        )
        logo_width = 70 * mm
        logo = svg('logos/lumina-fiocruz-claro.svg')
        draw_svg(
            canvas,
            'logos/lumina-fiocruz-claro.svg',
            20 * mm,
            PAGE_HEIGHT - 20 * mm - logo.height * logo_width / logo.width,
            width=logo_width,
        )
        canvas.restoreState()

        width = PAGE_WIDTH - 40 * mm
        y = PAGE_HEIGHT * 0.58
        for text, style in [
            (self.cover['kicker'], 'CoverKicker'),
            (self.cover['title'], 'CoverTitle'),
            (self.cover.get('subtitle'), 'CoverSubtitle'),
        ]:
            if not text:
                continue
            paragraph = Paragraph(escape(text), self.styles[style])
            _, height = paragraph.wrapOn(canvas, width, PAGE_HEIGHT)
            y -= height
            paragraph.drawOn(canvas, 20 * mm, y)
            y -= 6 * mm

        footer = Paragraph(
            f'{escape(self.cover["meta"])}<br/><b>{SITE}</b>',
            self.styles['CoverMeta'],
        )
        footer.wrapOn(canvas, width, PAGE_HEIGHT)
        footer.drawOn(canvas, 20 * mm, 20 * mm)

    def draw_inner(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(COR_FUNDO)
        canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)

        rail_top = PAGE_HEIGHT - MARGIN_TOP
        canvas.setStrokeColor(COR_LARANJA)
        canvas.setLineWidth(0.25 * mm)
        canvas.roundRect(
            RAIL_X,
            MARGIN_BOTTOM,
            RAIL_WIDTH,
            rail_top - MARGIN_BOTTOM,
            RAIL_WIDTH / 2,
            stroke=1,
            fill=0,
        )
        castle_width = 6 * mm
        castle = svg('logos/fiocruz-castelo-laranja.svg')
        castle_height = castle.height * castle_width / castle.width
        draw_svg(
            canvas,
            'logos/fiocruz-castelo-laranja.svg',
            RAIL_X + (RAIL_WIDTH - castle_width) / 2,
            rail_top - 4 * mm - castle_height,
            width=castle_width,
        )

        canvas.setFillColor(COR_TINTA)
        canvas.saveState()
        canvas.translate(RAIL_X + RAIL_WIDTH / 2 + 1 * mm, rail_top - 16 * mm)
        canvas.rotate(-90)
        canvas.setFont('Lexend-Bold', 8)
        canvas.drawString(0, 0, 'LUMINA')
        offset = pdfmetrics.stringWidth('LUMINA ', 'Lexend-Bold', 8)
        canvas.setFont('Lexend-Light', 8)
        canvas.drawString(offset, 0, self.rail_title)
        canvas.restoreState()

        canvas.setFont('Lexend-Light', 7)
        canvas.drawCentredString(
            RAIL_X + RAIL_WIDTH / 2, MARGIN_BOTTOM + 4 * mm, f'{doc.page:03d}'
        )

        canvas.setFont('Lexend-Light', 8)
        canvas.drawString(MARGIN_LEFT, 10 * mm, SITE)
        draw_svg(
            canvas,
            'logos/lumina-horizontal-laranja.svg',
            PAGE_WIDTH - MARGIN_RIGHT - 25 * mm,
            8 * mm,
            width=25 * mm,
        )
        canvas.restoreState()


def build_report(filepath, cover, rail_title, sections, styles):
    """Monta capa, sumário e uma seção por página e grava o PDF."""
    doc = LuminaDocTemplate(str(filepath), cover, rail_title, styles)
    toc = TableOfContents(levelStyles=[styles['TocEntry']], dotsMinLevel=0)
    story = [
        NextPageTemplate('interna'),
        PageBreak(),
        Paragraph('Sumário', styles['TocTitle']),
        toc,
    ]
    for number, (title, flowables) in enumerate(sections, start=1):
        story += [
            PageBreak(),
            Paragraph(f'{number:02d}', styles['SectionLabel']),
            Paragraph(escape(title), styles['SectionTitle']),
            *flowables,
        ]
    doc.multiBuild(story)


def markdown(text, styles):
    return markdown_to_flowables(text, styles, width=CONTENT_WIDTH)


def create_sources_section(sources, styles):
    elements = []
    if not sources:
        return elements

    elements.append(Paragraph('Fontes utilizadas', styles['Title3']))
    for s in sources:
        name = escape(s.get('name') or 'Sem nome')
        elements.append(
            Paragraph(
                f'<b>{name}</b> ({format_date(s.get("created_at"))})',
                styles['MdBullet'],
                bulletText='•',
            )
        )
        elements.extend(markdown(s.get('description'), styles))

    elements.append(Spacer(1, 6))
    return elements


def create_taxonomy_section(taxonomies, styles):
    elements = []
    for tax in taxonomies or []:
        elements.append(
            Paragraph(
                escape(tax.get('title') or 'Sem título'), styles['Title2']
            )
        )
        elements.extend(markdown(tax.get('description'), styles))

        for b in tax.get('branches') or []:
            elements.append(
                Paragraph(escape(b.get('title') or ''), styles['Criterion'])
            )
            elements.extend(markdown(b.get('description'), styles))

    return elements


def typification_report(data: dict, output_dir: str = 'lumina/storage/temp'):
    """
    Função principal para geração do PDF.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'lumina_report_{today}.pdf'
    filepath = Path(output_dir) / filename

    styles = get_custom_styles()
    typifications = data.get('typifications', [])

    sections = []
    for tipificacao in typifications:
        content = [
            Paragraph(
                f'Criado em {format_date(tipificacao.get("created_at"))}',
                styles['Meta'],
            ),
            *create_sources_section(tipificacao.get('sources'), styles),
            *create_taxonomy_section(tipificacao.get('taxonomies'), styles),
        ]
        sections.append((tipificacao.get('name') or 'Sem nome', content))

    title = (
        typifications[0].get('name')
        if len(typifications) == 1
        else 'Base de conhecimento'
    )
    cover = {
        'kicker': 'Relatório da base de conhecimento',
        'title': title or 'Base de conhecimento',
        'subtitle': f'{len(typifications)} tipificação(ões)',
        'meta': f'Gerado em {format_date(datetime.now())}',
    }

    try:
        build_report(filepath, cover, 'Base de conhecimento', sections, styles)
        return str(filepath)
    except Exception as e:
        print(f'Erro ao gerar PDF: {e}')
        return None


def create_evaluation_item(branch, styles):
    title = escape(branch.get('title') or 'Sem título')
    evaluation = branch.get('evaluation') or {}
    status = STATUS.get(evaluation.get('fulfilled'), STATUS[None])
    score = evaluation.get('score')
    score = '-' if score is None else score

    header = KeepTogether([
        Paragraph(title, styles['Criterion']),
        Paragraph(
            f'<b>Status:</b> {status} · <b>Nota:</b> {score}', styles['Meta']
        ),
    ])
    return [
        header,
        *markdown(evaluation.get('feedback'), styles),
        Spacer(1, 6),
    ]


def create_release_check_tree_section(check_tree, styles):
    sections = []
    for tip in check_tree or []:
        content = create_sources_section(tip.get('sources'), styles)
        for tax in tip.get('taxonomies') or []:
            content.append(
                Paragraph(
                    escape(tax.get('title') or 'Sem título'), styles['Title2']
                )
            )
            content.extend(markdown(tax.get('description'), styles))
            content.extend(create_sources_section(tax.get('sources'), styles))
            for b in tax.get('branches') or []:
                content.extend(create_evaluation_item(b, styles))
        sections.append((tip.get('name') or 'Tipificação sem nome', content))
    return sections


def document_release_report(
    data: dict, output_dir: str = 'lumina/storage/temp'
):
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'lumina_document_release_{today}.pdf'
    filepath = Path(output_dir) / filename

    styles = get_custom_styles()

    sections = []
    if data.get('description'):
        sections.append((
            'Síntese da avaliação',
            markdown(data['description'], styles),
        ))
    sections.extend(
        create_release_check_tree_section(data.get('check_tree'), styles)
    )

    version = data.get('version')
    cover = {
        'kicker': 'Relatório de avaliação',
        'title': data.get('document_name') or 'Documento',
        'subtitle': f'Versão {version}' if version else None,
        'meta': (
            f'Release de {format_date(data.get("created_at"))} · '
            f'gerado em {format_date(datetime.now())}'
        ),
    }

    try:
        build_report(
            filepath, cover, 'Relatório de avaliação', sections, styles
        )
        return str(filepath)
    except Exception:
        return None


async def generate_document_release_pdf(session, document_release_id: UUID):
    stmt = select(DocumentRelease).where(
        DocumentRelease.id == document_release_id
    )

    obj = await session.scalar(stmt)

    if not obj:
        return None

    payload = DocumentReleasePublic.model_validate(obj).model_dump()
    payload['document_name'] = await session.scalar(
        select(Document.name).where(Document.id == obj.document_id)
    )

    report_path = document_release_report(payload)

    if not report_path:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail='Could not generate PDF',
        )

    return report_path
