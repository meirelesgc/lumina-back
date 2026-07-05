# Verificação híbrida POR SEÇÃO (visual + determinística) entre um artigo e um
# template de revista. Três seções: elementos pré-textuais (p.1), textuais
# (p.2 + corpo) e pós-textuais (referências).
#
# Portado de template_abnt_feature/hybrid_template_comparison.py (dashboard
# Streamlit), removendo apenas o que era exclusivo de CLI (argparse, main(),
# persistência via storage.py -- agora feita por json_store.py). A lógica de
# negócio (prompts, tolerâncias, algoritmos de comparação) permanece intacta.
#
# Particularidades desta abordagem:
# - O critério "Número de colunas" NÃO compara a largura individual de cada
#   coluna (apenas a quantidade de colunas e o espaço entre elas).
# - Margens: 17 mm (superior/esquerda/direita); inferior 20 mm (tabelas/rodapés distorcem a bbox).
# - Espaçamento entre linhas usa leading absoluto com tolerância de 35 mm.
# - Não há critérios de "Numeração das páginas", "Alinhamento do texto" nem
#   "Recuo dos parágrafos" (determinísticos).
# - A fonte principal não compara mais o estilo "italic".
# - A formatação tipográfica das referências não compara mais o recuo das
#   linhas subsequentes ("recuo_linhas_subsequentes").
# - O prompt do modelo de visão é deliberadamente tolerante: só reprova diante
#   de divergência CLARA em margens, recuo dos parágrafos, layout geral ou
#   número de colunas; divergências leves em cabeçalho de evento, rodapé,
#   numeração de página, DOI, numeração de linhas na margem e marcadores/links
#   de referência cruzada ([CrossRef]/[PubMed]/URLs) geram apenas um alerta
#   textual (reasoning), sem reprovar o match. Na página de referências, o
#   modelo só analisa o trecho a partir do título "References". Como gpt-5 (modelo
#   de raciocínio) não aceita "temperature", usa-se reasoning.effort="minimal"
#   como aproximação para respostas mais determinísticas.

from __future__ import annotations

import asyncio
import base64

from openai import AsyncOpenAI
from pydantic import BaseModel

from iaEditais.features.template_abnt import pdf_metrics as m
from iaEditais.features.template_abnt.image_utils import render_page_png

# Configuração do modelo de visão.
VISION_MODEL = 'gpt-5'
VISION_DPI = 150
VISION_DETAIL = 'high'
# gpt-5 é um modelo de raciocínio e rejeita o parâmetro "temperature" (erro 400 da API).
# "minimal" é o nível de esforço de raciocínio mais próximo de baixa temperatura: reduz a
# variabilidade da resposta e é mais rápido/barato que os níveis mais altos.
VISION_REASONING_EFFORT = 'high'

# Tolerâncias de comparação determinística (mesma ordem de grandeza das outras abordagens).
PAGE_TOL_MM = 5.0
MARGIN_TOL_MM = 17.0
MARGIN_BOTTOM_TOL_MM = 20.0
GUTTER_TOL_MM = 4.0
FONT_SIZE_TOL_PT = 0.7
SPACING_TOL_MM = 35.0
PT_TO_MM = 25.4 / 72.0

SEC_PRE = 'elementos_pre_textuais'
SEC_TEXT = 'elementos_textuais'
SEC_POS = 'elementos_pos_textuais'
SEC_TITLES = {
    SEC_PRE: 'Seção de Elementos Pré-Textuais',
    SEC_TEXT: 'Seção de Elementos Textuais',
    SEC_POS: 'Seção de Elementos Pós-Textuais',
}


# --------------------------------------------------------------------------
# Schema (auto-contido neste arquivo).
# --------------------------------------------------------------------------

class Check(BaseModel):
    field: str
    template_value: str
    article_value: str
    match: bool


class VisualCriterionItem(BaseModel):
    criterio: str
    justificativa: str


class Criterion(BaseModel):
    id: str
    title: str
    match: bool
    is_visual: bool = False
    checks: list[Check] = []
    criterios: list[VisualCriterionItem] = []


class SectionResult(BaseModel):
    id: str
    title: str
    template_pages: list[int]
    article_pages: list[int]
    match: bool
    criteria: list[Criterion]


class Summary(BaseModel):
    is_compliant: bool
    secoes_total: int
    secoes_passed: int
    description: str


class Metadata(BaseModel):
    approach: str
    model: str
    template_file: str
    article_file: str


class HybridReport(BaseModel):
    metadata: Metadata
    summary: Summary
    secoes: list[SectionResult]


def build_report(metadata: Metadata, secoes: list[SectionResult], description: str) -> HybridReport:
    passed = sum(1 for s in secoes if s.match)
    summary = Summary(
        is_compliant=passed == len(secoes),
        secoes_total=len(secoes),
        secoes_passed=passed,
        description=description,
    )
    return HybridReport(metadata=metadata, summary=summary, secoes=secoes)


# --------------------------------------------------------------------------
# Formatação e predicados reutilizáveis (mesma lógica das demais abordagens).
# --------------------------------------------------------------------------

def fmt_mm(value: float) -> str:
    return f'{value:.1f} mm'


def fmt_pt(value: float) -> str:
    return f'{value:.1f} pt'


def fmt_bool(value: bool) -> str:
    return 'sim' if value else 'não'


def fmt_ratio(value: float | None) -> str:
    return 'indeterminado' if value is None else f'{value:.2f}'


def fmt_pages(pages: list[int]) -> str:
    return ', '.join(str(p) for p in pages) if pages else '—'


def within(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def normalize_family(name: str) -> str:
    base = name.lower()
    for token in ('-', '_', 'mt', 'ps', 'regular', 'roman'):
        base = base.replace(token, '')
    return ''.join(ch for ch in base if ch.isalpha())


def families_match(a: str, b: str) -> bool:
    na, nb = normalize_family(a), normalize_family(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


def make_check(field: str, template: str, article: str, match: bool) -> Check:
    return Check(field=field, template_value=template, article_value=article, match=match)


def all_match(checks: list[Check]) -> bool:
    return all(c.match for c in checks) if checks else False


def make_script_criterion(cid: str, title: str, checks: list[Check]) -> Criterion:
    return Criterion(id=cid, title=title, match=all_match(checks), is_visual=False, checks=checks)


def make_visual_criterion(cid: str, title: str, match: bool,
                          criterios: list[VisualCriterionItem]) -> Criterion:
    return Criterion(id=cid, title=title, match=match, is_visual=True, criterios=criterios)


# --------------------------------------------------------------------------
# Builders determinísticos de critério, operando sobre perfis de página
# (dicts retornados por pdf_metrics.extract_page_metrics/aggregate_page_metrics).
# Reaproveitados tanto para a página 1 (página única vs página única) quanto
# para a página 2 (página única vs perfil agregado de várias páginas do artigo).
# --------------------------------------------------------------------------

def build_page_size(tpl: dict, art: dict) -> Criterion:
    checks = [
        make_check('formato', tpl['page_format'], art['page_format'],
                   tpl['page_format'] == art['page_format']),
        make_check('largura', fmt_mm(tpl['width_mm']), fmt_mm(art['width_mm']),
                   within(tpl['width_mm'], art['width_mm'], PAGE_TOL_MM)),
        make_check('altura', fmt_mm(tpl['height_mm']), fmt_mm(art['height_mm']),
                   within(tpl['height_mm'], art['height_mm'], PAGE_TOL_MM)),
    ]
    return make_script_criterion('page_size', 'Tamanho da página', checks)


def build_columns(tpl: dict, art: dict) -> Criterion:
    checks = [
        make_check('numero_colunas', str(tpl['column_count']), str(art['column_count']),
                   tpl['column_count'] == art['column_count']),
        make_check('espaco_entre_colunas', fmt_mm(tpl['gutter_mm']), fmt_mm(art['gutter_mm']),
                   within(tpl['gutter_mm'], art['gutter_mm'], GUTTER_TOL_MM)),
    ]
    return make_script_criterion('columns', 'Número de colunas', checks)


def build_margins(tpl: dict, art: dict) -> Criterion:
    sides = ['top', 'bottom', 'left', 'right']
    labels = {'top': 'superior', 'bottom': 'inferior', 'left': 'esquerda', 'right': 'direita'}
    tolerances = {'top': MARGIN_TOL_MM, 'bottom': MARGIN_BOTTOM_TOL_MM,
                  'left': MARGIN_TOL_MM, 'right': MARGIN_TOL_MM}
    checks = [
        make_check(
            labels[side],
            fmt_mm(tpl['margins_mm'][side]),
            fmt_mm(art['margins_mm'][side]),
            within(tpl['margins_mm'][side], art['margins_mm'][side], tolerances[side]),
        )
        for side in sides
    ]
    return make_script_criterion('margins', 'Margens', checks)


def build_main_font(tpl: dict, art: dict) -> Criterion:
    checks = [
        make_check('familia', tpl['font_family'], art['font_family'],
                   families_match(tpl['font_family'], art['font_family'])),
        make_check('tamanho', fmt_pt(tpl['font_size_pt']), fmt_pt(art['font_size_pt']),
                   within(tpl['font_size_pt'], art['font_size_pt'], FONT_SIZE_TOL_PT)),
        make_check('bold', fmt_bool(tpl['font_bold']), fmt_bool(art['font_bold']),
                   tpl['font_bold'] == art['font_bold']),
        make_check('cor', tpl['font_color'], art['font_color'],
                   tpl['font_color'] == art['font_color']),
    ]
    return make_script_criterion('main_font', 'Fonte principal do texto', checks)


def leading_mm(profile: dict) -> float | None:
    ratio, size = profile.get('spacing_ratio'), profile.get('font_size_pt')
    if ratio is None or not size:
        return None
    return ratio * size * PT_TO_MM


def build_line_spacing(tpl: dict, art: dict) -> Criterion:
    tpl_lead, art_lead = leading_mm(tpl), leading_mm(art)
    leading_ok = (
        tpl_lead is not None and art_lead is not None
        and within(tpl_lead, art_lead, SPACING_TOL_MM)
    )
    checks = [
        make_check('modo', tpl['spacing_mode'], art['spacing_mode'], leading_ok),
        make_check('leading', fmt_mm(tpl_lead) if tpl_lead else 'indeterminado',
                   fmt_mm(art_lead) if art_lead else 'indeterminado', leading_ok),
        make_check('razao', fmt_ratio(tpl['spacing_ratio']), fmt_ratio(art['spacing_ratio']),
                   leading_ok),
    ]
    return Criterion(
        id='line_spacing',
        title='Espaçamento entre linhas',
        match=leading_ok,
        is_visual=False,
        checks=checks,
    )


PAGE_BUILDERS = [
    build_page_size,
    build_columns,
    build_margins,
    build_main_font,
    build_line_spacing,
]

# Página 1: capa/instruções do template distorcem margens superiores; visual cobre layout.
PAGE1_BUILDERS = [build_page_size, build_columns, build_main_font, build_line_spacing]


def build_references_typography(tpl_ref: dict | None, art_ref: dict | None) -> Criterion:
    if not tpl_ref or not art_ref:
        checks = [make_check('secao_localizada', fmt_bool(bool(tpl_ref)), fmt_bool(bool(art_ref)),
                              bool(tpl_ref) == bool(art_ref))]
        return make_script_criterion('references_typography', 'Formatação tipográfica das referências', checks)
    checks = [
        make_check('familia_fonte', tpl_ref['font_family'], art_ref['font_family'],
                   families_match(tpl_ref['font_family'], art_ref['font_family'])),
        make_check('tamanho_fonte', fmt_pt(tpl_ref['font_size_pt']), fmt_pt(art_ref['font_size_pt']),
                   within(tpl_ref['font_size_pt'], art_ref['font_size_pt'], FONT_SIZE_TOL_PT)),
        make_check('alinhamento', tpl_ref['text_alignment'], art_ref['text_alignment'],
                   tpl_ref['text_alignment'] == art_ref['text_alignment']),
        make_check('estilo_numeracao', tpl_ref['numbering_style'], art_ref['numbering_style'],
                   tpl_ref['numbering_style'] == art_ref['numbering_style']),
    ]
    return make_script_criterion('references_typography', 'Formatação tipográfica das referências', checks)


def missing_page_criterion(cid: str, title: str, reason: str) -> Criterion:
    checks = [make_check('pagina_disponivel', 'sim', 'não', False)]
    return make_script_criterion(cid, title, checks)


# --------------------------------------------------------------------------
# Localização e amostragem de páginas (template/artigo).
# --------------------------------------------------------------------------

def first_page_bounds(bounds: dict) -> dict:
    # Restringe os limites da seção de referências à PRIMEIRA página apenas
    # (usado para o lado do template, que só entra na comparação pela 1a página).
    return {
        'start_page': bounds['start_page'],
        'start_y': bounds['start_y'],
        'end_page': bounds['start_page'],
        'end_y': None,
    }


def body_candidate_pages(doc, ref_bounds: dict | None) -> list[int]:
    # Todas as páginas do artigo, exceto a primeira e as pertencentes à seção
    # de referências (usado para o scan determinístico da página 2).
    exclude = {1}
    if ref_bounds:
        exclude |= set(range(ref_bounds['start_page'], ref_bounds['end_page'] + 1))
    candidates = [p for p in range(1, doc.page_count + 1) if p not in exclude]
    return candidates or [min(2, doc.page_count)]


def compute_bounds(template_path: str, article_path: str) -> tuple[dict | None, dict | None, int, int]:
    # Abre os dois documentos uma única vez para descobrir os limites da seção
    # de referências e a contagem de páginas; roda em thread (via asyncio.to_thread)
    # antes de disparar as 3 tarefas de página, que depois abrem seus PRÓPRIOS
    # handles de documento (PyMuPDF não é seguro para compartilhar um mesmo
    # objeto Document entre threads concorrentes).
    tpl_doc = m.open_document(template_path)
    art_doc = m.open_document(article_path)
    try:
        tpl_bounds = m.find_references_bounds(tpl_doc)
        art_bounds = m.find_references_bounds(art_doc)
        return tpl_bounds, art_bounds, tpl_doc.page_count, art_doc.page_count
    finally:
        tpl_doc.close()
        art_doc.close()


# --------------------------------------------------------------------------
# Verificação determinística por página (orquestração dos builders acima).
# Cada função abre e fecha seus PRÓPRIOS handles de documento (thread-safe,
# pois roda em paralelo com as demais páginas via asyncio.to_thread).
# --------------------------------------------------------------------------

def run_script_page1(template_path: str, article_path: str) -> list[Criterion]:
    tpl_doc = m.open_document(template_path)
    art_doc = m.open_document(article_path)
    try:
        if tpl_doc.page_count < 1 or art_doc.page_count < 1:
            return [missing_page_criterion('page_1_scan', 'Scan determinístico - Página 1',
                                            'Um dos documentos não possui a primeira página.')]
        tpl = m.extract_page_metrics(tpl_doc, 1)
        art = m.extract_page_metrics(art_doc, 1)
        return [build(tpl, art) for build in PAGE1_BUILDERS]
    finally:
        tpl_doc.close()
        art_doc.close()


def run_script_page2(template_path: str, article_path: str,
                      art_bounds: dict | None) -> tuple[list[Criterion], list[int]]:
    tpl_doc = m.open_document(template_path)
    art_doc = m.open_document(article_path)
    try:
        if tpl_doc.page_count < 2:
            return [missing_page_criterion('page_2_scan', 'Scan determinístico - Página 2',
                                            'O template não possui uma segunda página.')], []
        if art_doc.page_count < 2:
            return [missing_page_criterion('page_2_scan', 'Scan determinístico - Página 2',
                                            'O artigo não possui uma segunda página.')], []
        tpl = m.extract_page_metrics(tpl_doc, 2)
        candidate_pages = body_candidate_pages(art_doc, art_bounds)
        art = m.aggregate_page_metrics([m.extract_page_metrics(art_doc, p) for p in candidate_pages])
        criteria = [build(tpl, art) for build in PAGE_BUILDERS]
        return criteria, candidate_pages
    finally:
        tpl_doc.close()
        art_doc.close()


def run_script_references(template_path: str, article_path: str, tpl_bounds: dict | None,
                           art_bounds: dict | None) -> tuple[list[Criterion], list[int], list[int]]:
    tpl_pages = [tpl_bounds['start_page']] if tpl_bounds else []
    art_pages = list(range(art_bounds['start_page'], art_bounds['end_page'] + 1)) if art_bounds else []
    tpl_doc = m.open_document(template_path)
    art_doc = m.open_document(article_path)
    try:
        tpl_ref = m.extract_references_metrics(tpl_doc, first_page_bounds(tpl_bounds)) if tpl_bounds else None
        art_ref = m.extract_references_metrics(art_doc, art_bounds) if art_bounds else None
    finally:
        tpl_doc.close()
        art_doc.close()
    return [build_references_typography(tpl_ref, art_ref)], tpl_pages, art_pages


# --------------------------------------------------------------------------
# Verificação visual (modelo de visão da OpenAI) por página — assíncrona.
# --------------------------------------------------------------------------

class VisualComparisonResult(BaseModel):
    match: bool
    confidence: float
    criterios: list[VisualCriterionItem]


def to_data_url(png_bytes: bytes) -> str:
    encoded = base64.b64encode(png_bytes).decode()
    return f'data:image/png;base64,{encoded}'


def image_block(png_bytes: bytes, detail: str = VISION_DETAIL) -> dict:
    return {'type': 'input_image', 'image_url': to_data_url(png_bytes), 'detail': detail}


def text_block(text: str) -> dict:
    return {'type': 'input_text', 'text': text}


def build_visual_prompt(label: str) -> str:
    references_note = ''
    if 'referências' in label.lower() or 'pós-textuais' in label.lower():
        references_note = (
            '\n- Esta é a seção pós-textual (referências): analise **apenas a partir do título '
            '"References"/"Referências" (ou equivalente)** até o final da página. Ignore conteúdo '
            'acima desse título.'
        )
    return f"""# Papel
- Especialista em editoração científica e diagramação de periódicos acadêmicos.
- Compare visualmente duas imagens: a seção "{label}" do TEMPLATE e a seção correspondente do ARTIGO.

# Objetivo
Verificar se a diagramação visual do ARTIGO apresenta **inconformidade grave** em relação ao TEMPLATE.
Pequenas variações são normais e não devem reprovar.

# Instruções
- Analise apenas layout/diagramação — NÃO avalie o conteúdo textual em si.
- Reprove (match = false) só diante de divergência clara e acentuada; na dúvida, aprove.
- confidence: número entre 0 e 1.{references_note}

## Pode reprovar (match = false)
- Margens visivelmente muito diferentes.
- Recuo dos parágrafos claramente diferente.
- Layout geral totalmente distinto.
- Número de colunas diferente.
- Alinhamento e estilo de numeração das referências (quando aplicável).

## Apenas alertar (mantenha match = true)
- Cabeçalho, rodapé, DOI, numeração de página, links [CrossRef]/URLs, variações leves de espaçamento.

## Ignorar (verificados por script)
- Dimensões exatas da página, fonte do corpo, leading, fonte das referências.

# Formato de saída (obrigatório)
Retorne o campo **criterios**: array com um item por aspecto visual avaliado.
Cada item deve ter:
- **criterio**: nome curto do aspecto (ex.: "Margens", "Número de colunas", "Layout geral").
- **justificativa**: o que foi observado no template vs artigo (inclua divergências leves como alerta).

Exemplos:
[
  {{"criterio": "Margens", "justificativa": "Margens laterais equivalentes; leve variação no topo, aceitável."}},
  {{"criterio": "Número de colunas", "justificativa": "Ambas em coluna única."}},
  {{"criterio": "Layout geral", "justificativa": "Estrutura compatível; artigo sem figura presente no template, diferença de conteúdo."}}
]

Registre todos os aspectos relevantes da lista acima, mesmo quando compatíveis.
Use linguagem clara e objetiva."""


def render_page_safe(path: str, page_number: int | None, dpi: int = VISION_DPI) -> bytes | None:
    if not page_number:
        return None
    try:
        return render_page_png(path, page_number=page_number, dpi=dpi)
    except Exception:
        return None


async def visual_compare(client: AsyncOpenAI, template_png: bytes, article_png: bytes,
                          label: str) -> VisualComparisonResult:
    content = [
        text_block(f'TEMPLATE - {label}:'), image_block(template_png),
        text_block(f'ARTIGO - {label}:'), image_block(article_png),
    ]
    response = await client.responses.parse(
        model=VISION_MODEL,
        instructions=build_visual_prompt(label),
        input=[{'role': 'user', 'content': content}],
        text_format=VisualComparisonResult,
        reasoning={'effort': VISION_REASONING_EFFORT},
    )
    result = response.output_parsed
    if result is None:
        raise RuntimeError('Modelo de visão não retornou uma saída estruturada (possível refusal).')
    return result


async def run_visual_check(client: AsyncOpenAI | None, section_id: str, label: str, template_path: str,
                            template_page: int | None, article_path: str, article_page: int | None,
                            skip_visual: bool) -> Criterion:
    visual_id = f'{section_id}_visual'
    visual_title = f'Verificação visual — {label}'

    if skip_visual:
        return make_visual_criterion(
            visual_id, visual_title, True,
            [VisualCriterionItem(criterio='Verificação visual',
                                 justificativa='Comparação visual não executada (--skip-visual).')],
        )

    tpl_png, art_png = await asyncio.gather(
        asyncio.to_thread(render_page_safe, template_path, template_page),
        asyncio.to_thread(render_page_safe, article_path, article_page),
    )
    if tpl_png is None or art_png is None:
        missing = 'template' if tpl_png is None else 'artigo'
        return make_visual_criterion(
            visual_id, visual_title, False,
            [VisualCriterionItem(
                criterio='Disponibilidade da página',
                justificativa=f'Não foi possível renderizar a página correspondente no {missing}.',
            )],
        )

    try:
        result = await visual_compare(client, tpl_png, art_png, label)
    except Exception as exc:
        return make_visual_criterion(
            visual_id, visual_title, False,
            [VisualCriterionItem(criterio='Consulta ao modelo de visão',
                                 justificativa=f'Falha ao consultar o modelo: {exc}')],
        )

    return make_visual_criterion(visual_id, visual_title, result.match, result.criterios)


# --------------------------------------------------------------------------
# Orquestração híbrida (visual + determinística), por página — assíncrona.
# As 3 páginas rodam concorrentemente (asyncio.gather em compare()); dentro de
# cada página, a verificação visual e a determinística também rodam em paralelo.
# --------------------------------------------------------------------------

def build_section_result(section_id: str, title: str, template_pages: list[int], article_pages: list[int],
                         visual_criterion: Criterion, script_criteria: list[Criterion]) -> SectionResult:
    criteria = [visual_criterion, *script_criteria]
    return SectionResult(
        id=section_id, title=title, template_pages=template_pages, article_pages=article_pages,
        match=all(c.match for c in criteria), criteria=criteria,
    )


async def run_pre_textual_task(client: AsyncOpenAI | None, template_path: str, article_path: str,
                                tpl_page_count: int, art_page_count: int, skip_visual: bool) -> SectionResult:
    visual, script_criteria = await asyncio.gather(
        run_visual_check(client, SEC_PRE, SEC_TITLES[SEC_PRE], template_path, 1, article_path, 1, skip_visual),
        asyncio.to_thread(run_script_page1, template_path, article_path),
    )
    return build_section_result(
        SEC_PRE, SEC_TITLES[SEC_PRE],
        [1] if tpl_page_count >= 1 else [],
        [1] if art_page_count >= 1 else [],
        visual, script_criteria,
    )


async def run_textual_task(client: AsyncOpenAI | None, template_path: str, article_path: str,
                            art_bounds: dict | None, tpl_page_count: int, art_page_count: int,
                            skip_visual: bool) -> SectionResult:
    tpl_p2 = 2 if tpl_page_count >= 2 else None
    art_p2 = 2 if art_page_count >= 2 else None
    visual, (script_criteria, art_p2_pages) = await asyncio.gather(
        run_visual_check(client, SEC_TEXT, SEC_TITLES[SEC_TEXT], template_path, tpl_p2, article_path, art_p2, skip_visual),
        asyncio.to_thread(run_script_page2, template_path, article_path, art_bounds),
    )
    return build_section_result(
        SEC_TEXT, SEC_TITLES[SEC_TEXT],
        [tpl_p2] if tpl_p2 else [], art_p2_pages, visual, script_criteria,
    )


async def run_pos_textual_task(client: AsyncOpenAI | None, template_path: str, article_path: str,
                                tpl_bounds: dict | None, art_bounds: dict | None,
                                skip_visual: bool) -> SectionResult:
    tpl_ref_page = tpl_bounds['start_page'] if tpl_bounds else None
    art_ref_page = art_bounds['start_page'] if art_bounds else None
    visual, (script_criteria, tpl_ref_pages, art_ref_pages) = await asyncio.gather(
        run_visual_check(client, SEC_POS, SEC_TITLES[SEC_POS], template_path, tpl_ref_page,
                          article_path, art_ref_page, skip_visual),
        asyncio.to_thread(run_script_references, template_path, article_path, tpl_bounds, art_bounds),
    )
    return build_section_result(
        SEC_POS, SEC_TITLES[SEC_POS], tpl_ref_pages, art_ref_pages, visual, script_criteria,
    )


async def compare(template_path: str, article_path: str, skip_visual: bool = False) -> HybridReport:
    client = None if skip_visual else AsyncOpenAI()
    try:
        tpl_bounds, art_bounds, tpl_page_count, art_page_count = await asyncio.to_thread(
            compute_bounds, template_path, article_path
        )

        sec_pre, sec_text, sec_pos = await asyncio.gather(
            run_pre_textual_task(client, template_path, article_path, tpl_page_count, art_page_count, skip_visual),
            run_textual_task(client, template_path, article_path, art_bounds, tpl_page_count, art_page_count, skip_visual),
            run_pos_textual_task(client, template_path, article_path, tpl_bounds, art_bounds, skip_visual),
        )
    finally:
        if client is not None:
            await client.close()

    secoes = [sec_pre, sec_text, sec_pos]
    metadata = Metadata(
        approach='hybrid_visual',
        model='—' if skip_visual else VISION_MODEL,
        template_file=template_path,
        article_file=article_path,
    )
    description = (
        'Abordagem híbrida por seção (pré-textuais, textuais e pós-textuais): verificação '
        'visual (modelo de visão) e determinística (PyMuPDF). O scan textual agrega as '
        'páginas de corpo do artigo; o pós-textual agrega todas as páginas de referências.'
    )
    return build_report(metadata, secoes, description)
