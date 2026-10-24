"""Converte Markdown em Flowables do ReportLab.

Cobre o subconjunto que os modelos usam nas sínteses e pareceres: títulos,
listas, negrito, itálico, código, tabelas GFM e blocos de código. Todo texto
é escapado antes de receber as tags do ReportLab, então `<` e `&` vindos do
conteúdo nunca quebram o parser de XML.
"""

import re
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.lib.units import cm
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    Paragraph,
    Preformatted,
    Table,
    TableStyle,
)

# Tokens do design system (lumina/assets/design-system/tokens/tokens.json)
TABLE_HEADER_BACKGROUND = colors.HexColor('#0e90a0')
TABLE_HEADER_TEXT = colors.HexColor('#efefef')
TABLE_LINE = colors.HexColor('#d6d6d6')

LIST_INDENT = 12

HEADING_RE = re.compile(r'^(#{1,6})\s+(.*?)\s*#*\s*$')
LIST_RE = re.compile(r'^(\s*)([-*+]|\d+[.)])\s+(.*)$')
RULE_RE = re.compile(r'^\s*([-*_])(\s*\1){2,}\s*$')
FENCE_RE = re.compile(r'^\s*```')
TABLE_SEPARATOR_RE = re.compile(r'^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$')
QUOTE_RE = re.compile(r'^\s*>\s?')

CODE_SPAN_RE = re.compile(r'`([^`]+)`')
BOLD_RE = re.compile(r'\*\*(?=\S)(.+?)(?<=\S)\*\*|__(?=\S)(.+?)(?<=\S)__')
ITALIC_RE = re.compile(
    r'(?<![*\w])\*(?=\S)(.+?)(?<=\S)\*(?!\*)'
    r'|(?<![_\w])_(?=\S)(.+?)(?<=\S)_(?![_\w])'
)


def markdown_styles(
    body_font='Helvetica',
    heading_font='Helvetica-Bold',
    text_color=colors.black,
    heading_color=colors.black,
    subheading_color=colors.black,
):
    """Estilos que `markdown_to_flowables` procura pelo nome."""
    styles = StyleSheet1()
    body = ParagraphStyle(
        name='MdBody',
        fontName=body_font,
        fontSize=10,
        leading=15.5,
        spaceAfter=6,
        textColor=text_color,
        alignment=TA_LEFT,
    )
    styles.add(body)
    for level, (size, color) in enumerate(
        [(16, heading_color), (13, heading_color), (11, subheading_color)],
        start=1,
    ):
        styles.add(
            ParagraphStyle(
                name=f'MdHeading{level}',
                parent=body,
                fontName=heading_font,
                fontSize=size,
                leading=size * 1.2,
                spaceBefore=8,
                spaceAfter=4,
                textColor=color,
            )
        )
    styles.add(
        ParagraphStyle(
            name='MdBullet',
            parent=body,
            leftIndent=LIST_INDENT * 1.5,
            bulletIndent=LIST_INDENT * 0.5,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name='MdTableCell',
            parent=body,
            fontSize=9,
            leading=12,
            spaceAfter=0,
        )
    )
    styles.add(
        ParagraphStyle(
            name='MdTableHeader',
            parent=styles['MdTableCell'],
            fontName=heading_font,
            textColor=TABLE_HEADER_TEXT,
        )
    )
    styles.add(
        ParagraphStyle(
            name='MdCode',
            parent=body,
            fontName='Courier',
            fontSize=8.5,
            leading=11,
            leftIndent=LIST_INDENT,
        )
    )
    return styles


def inline_markup(text):
    """Escapa o texto e troca ênfases e código por tags do ReportLab."""
    codes = []

    def keep_code(match):
        codes.append(match.group(1))
        return f'\x00{len(codes) - 1}\x00'

    text = escape(text, quote=False)
    text = CODE_SPAN_RE.sub(keep_code, text)
    text = BOLD_RE.sub(lambda m: f'<b>{m.group(1) or m.group(2)}</b>', text)
    text = ITALIC_RE.sub(lambda m: f'<i>{m.group(1) or m.group(2)}</i>', text)
    return re.sub(
        r'\x00(\d+)\x00',
        lambda m: f'<font face="Courier">{codes[int(m.group(1))]}</font>',
        text,
    )


def split_row(line):
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]
    return [cell.strip() for cell in line.split('|')]


def is_table_start(lines, index):
    return (
        '|' in lines[index]
        and index + 1 < len(lines)
        and '-' in lines[index + 1]
        and TABLE_SEPARATOR_RE.match(lines[index + 1]) is not None
    )


def build_table(rows, styles, width):
    columns = len(rows[0])
    data = []
    for position, row in enumerate(rows):
        cells = (row + [''] * columns)[:columns]
        style = styles['MdTableHeader' if position == 0 else 'MdTableCell']
        data.append([Paragraph(inline_markup(cell), style) for cell in cells])

    table = Table(data, colWidths=[width / columns] * columns, repeatRows=1)
    table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_BACKGROUND),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, TABLE_LINE),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ])
    )
    return table


def list_item(match, styles):
    indent, marker, content = match.groups()
    level = min(len(indent.expandtabs(4)) // 2, 3)
    base = styles['MdBullet']
    style = base
    if level:
        style = ParagraphStyle(
            name=f'MdBullet{level}',
            parent=base,
            leftIndent=base.leftIndent + level * LIST_INDENT,
            bulletIndent=base.bulletIndent + level * LIST_INDENT,
        )
    bullet = '•' if marker in '-*+' else f'{marker[:-1]}.'
    return Paragraph(inline_markup(content), style, bulletText=bullet)


def markdown_to_flowables(
    text: str | None, styles: StyleSheet1, width: float = 15 * cm
) -> list[Flowable]:
    """Converte Markdown em Flowables usando os estilos `Md*` de `styles`.

    Texto sem marcação vira parágrafos, com as quebras de linha preservadas.
    """
    if not text or not text.strip():
        return []

    lines = text.replace('\r\n', '\n').split('\n')
    flowables = []
    paragraph = []

    def flush_paragraph():
        if paragraph:
            flowables.append(
                Paragraph(
                    '<br/>'.join(inline_markup(line) for line in paragraph),
                    styles['MdBody'],
                )
            )
            paragraph.clear()

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            index += 1
            continue

        if FENCE_RE.match(line):
            flush_paragraph()
            index += 1
            code = []
            while index < len(lines) and not FENCE_RE.match(lines[index]):
                code.append(lines[index])
                index += 1
            flowables.append(Preformatted('\n'.join(code), styles['MdCode']))
            index += 1
            continue

        if is_table_start(lines, index):
            flush_paragraph()
            rows = [split_row(line)]
            index += 2
            while index < len(lines) and '|' in lines[index]:
                rows.append(split_row(lines[index]))
                index += 1
            flowables.append(build_table(rows, styles, width))
            continue

        if heading := HEADING_RE.match(stripped):
            flush_paragraph()
            level = min(len(heading.group(1)), 3)
            flowables.append(
                Paragraph(
                    inline_markup(heading.group(2)),
                    styles[f'MdHeading{level}'],
                )
            )
        elif RULE_RE.match(line):
            flush_paragraph()
            flowables.append(
                HRFlowable(
                    width='100%',
                    thickness=0.5,
                    color=TABLE_LINE,
                    spaceBefore=4,
                    spaceAfter=6,
                )
            )
        elif item := LIST_RE.match(line):
            flush_paragraph()
            flowables.append(list_item(item, styles))
        else:
            paragraph.append(QUOTE_RE.sub('', stripped))

        index += 1

    flush_paragraph()
    return flowables
