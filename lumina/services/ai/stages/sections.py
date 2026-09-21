import re
from abc import ABC, abstractmethod
from collections import Counter
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from lumina.services.ai.stages.section_models import (
    Heading,
    Section,
    SectionRole,
)
from lumina.services.run_logger import get_run_logger

DEFAULT_SECTION_TITLE: str = 'NÃO ENCONTRADA'

HeadingCleaner = Callable[[List[Heading], str], List[Heading]]

HEADING_PATTERN = re.compile(r'^(#{1,6})\s*(.*)$')

NUMBERING_PATTERNS: List[Tuple[re.Pattern[str], int]] = [
    (re.compile(r'^\d+\.\d+\.\d+\.\d+'), 4),
    (re.compile(r'^\d+\.\d+\.\d+'), 3),
    (re.compile(r'^\d+\.[1-9]\d*'), 2),
    (re.compile(r'^\d+(\.0+)?\.?\s*[-–:]?\s+'), 1),
    (re.compile(r'^CL[ÁA]USULA\s+[IVXLCDM\d]+', re.IGNORECASE), 1),
    (re.compile(r'^ANEXO\s+[IVXLCDM\d]+', re.IGNORECASE), 1),
    (
        re.compile(
            r'^(TERMO DE REFER[ÊE]NCIA|PRE[ÂA]MBULO|EDITAL)\b', re.IGNORECASE
        ),
        1,
    ),
]

ROLE_ALIASES: Dict[SectionRole, List[str]] = {
    SectionRole.ABSTRACT: [
        r'^resumo$',
        r'^abstract$',
        r'^resumo\s*/\s*abstract$',
        r'^resumen$',
        r'^summary$',
        r'^sinopse$',
    ],
    SectionRole.INTRODUCTION: [
        r'^\d*\.?\s*introdu[çc][ãa]o$',
        r'^\d*\.?\s*introduction$',
        r'^1\.?\s*introdu[çc][ãa]o$',
        r'^1\.?\s*introduction$',
    ],
    SectionRole.METHODOLOGY: [
        r'materials?\s+and\s+methods?',
        r'materiais?\s+e\s+m[ée]todos?',
        r'materiais?\s+e\s+procedimentos?',
        r'metodologia',
        r'methodology',
        r'm[ée]todos?',
        r'methods?',
        r'procedimentos?\s+metodol[óo]gicos?',
    ],
    SectionRole.RESULTS: [
        r'^\d*\.?\s*resultados?$',
        r'^\d*\.?\s*results?$',
        r'resultados?\s+e\s+discuss[ãa]o',
        r'results?\s+and\s+discussion',
    ],
    SectionRole.DISCUSSION: [
        r'^\d*\.?\s*discuss[ãa]o$',
        r'^\d*\.?\s*discussion$',
    ],
    SectionRole.CONCLUSION: [
        r'conclus[ãa]o',
        r'conclus[õo]es',
        r'conclusion',
        r'conclusions?',
        r'concluding\s+remarks',
        r'considera[çc][õo]es\s+finais',
    ],
    SectionRole.REFERENCES: [
        r'refer[êe]ncias',
        r'refer[êe]ncias\s+bibliogr[áa]ficas',
        r'references',
        r'bibliography',
    ],
}


class SectionInfo(BaseModel):
    section_name: str = Field(description='Nome normalizado da seção.')
    start_text: Optional[str] = Field(
        default=None,
        description='Trecho exato inicial da seção.',
    )
    end_text: Optional[str] = Field(
        default=None,
        description='Trecho exato final da seção.',
    )


class ChunkSections(BaseModel):
    sections: List[SectionInfo] = Field(default_factory=list)


def strip_markup(text: str) -> str:
    """
    Remove marcações Markdown (**, *, __, _, ~~) e tags HTML (<u>, <mark>).
    """
    cleaned = re.sub(r'(\*\*|__|\*|_|~~)', '', text)
    cleaned = re.sub(r'</?[a-zA-Z0-9_-]+[^>]*>', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()


def text_between(full_text: str, h1: Heading, h2: Heading) -> str:
    """
    Retorna o texto delimitado entre a linha de h1 e a linha de h2.
    """
    lines = full_text.splitlines()
    start_line = h1.line_number
    end_line = h2.line_number - 1
    if start_line > end_line:
        return ''
    return '\n'.join(lines[start_line:end_line])


def clean_markup(headings: List[Heading], full_text: str) -> List[Heading]:
    """
    Passo 1 da Pipeline: Normaliza texto sem efeitos colaterais estruturais.
    """
    for h in headings:
        h.title = strip_markup(h.title)
    return headings


def normalize_title_for_counting(title: str) -> str:
    """
    Normaliza título para detecção de repetições por página.
    """
    return re.sub(r'[^\w]+', '', title.lower())


def make_repeated_cleaner(min_occurrences: int = 3) -> HeadingCleaner:
    """
    Passo 2 da Pipeline: Remove ruído repetido de cabeçalho/rodapé.
    """

    def cleaner(headings: List[Heading], full_text: str) -> List[Heading]:
        counts = Counter(
            normalize_title_for_counting(h.title)
            for h in headings
            if normalize_title_for_counting(h.title)
        )
        filtered: List[Heading] = []
        for h in headings:
            norm = normalize_title_for_counting(h.title)
            if not norm or counts[norm] < min_occurrences:
                filtered.append(h)
        return filtered

    return cleaner


def make_adjacent_merger(max_gap_chars: int = 5) -> HeadingCleaner:
    """
    Passo 3 da Pipeline: Funde títulos adjacentes em linhas contínuas.
    """

    def cleaner(headings: List[Heading], full_text: str) -> List[Heading]:
        if not headings:
            return []

        merged: List[Heading] = []
        i = 0
        total = len(headings)

        while i < total:
            current = headings[i]
            while i + 1 < total:
                nxt = headings[i + 1]
                gap = text_between(full_text, current, nxt)
                if len(gap.strip()) <= max_gap_chars:
                    current.title = f'{current.title} {nxt.title}'.strip()
                    current.raw = f'{current.raw} {nxt.raw}'.strip()
                    i += 1
                else:
                    break
            merged.append(current)
            i += 1

        return merged

    return cleaner


def reclassify_numbering_level(
    headings: List[Heading], full_text: str
) -> List[Heading]:
    """
    Passo 4 da Pipeline: Corrige o nível com base na numeração explícita.
    """
    for h in headings:
        matched = False
        clean_title = strip_markup(h.title)
        for pattern, level in NUMBERING_PATTERNS:
            if pattern.search(clean_title):
                h.level = level
                h.level_source = 'numbering_pattern'
                matched = True
                break
        if not matched:
            h.level_source = 'font'
    return headings


def make_orphan_cleaner(min_chars: int = 20) -> HeadingCleaner:
    """
    Passo 5 da Pipeline: Remove ruídos residuais genuínos.
    """

    def cleaner(headings: List[Heading], full_text: str) -> List[Heading]:
        if not headings:
            return []

        lines = full_text.splitlines()
        total_lines = len(lines)
        filtered: List[Heading] = []

        for i, h in enumerate(headings):
            start_line = h.line_number
            end_line = (
                headings[i + 1].line_number - 1
                if i + 1 < len(headings)
                else total_lines
            )

            section_lines = lines[start_line:end_line]
            section_text = '\n'.join(section_lines).strip()

            if len(section_text) >= min_chars:
                filtered.append(h)
            elif i + 1 < len(headings) and headings[i + 1].level > h.level:
                filtered.append(h)
            elif h.level_source == 'numbering_pattern' and i + 1 < len(
                headings
            ):
                filtered.append(h)

        return filtered

    return cleaner


def get_default_heading_cleaners() -> List[HeadingCleaner]:
    """
    Retorna a sequência padrão ordenada dos 5 cleaners funcionais.
    """
    return [
        clean_markup,
        make_repeated_cleaner(min_occurrences=3),
        make_adjacent_merger(max_gap_chars=5),
        reclassify_numbering_level,
        make_orphan_cleaner(min_chars=20),
    ]


def run_heading_pipeline(
    headings: List[Heading],
    full_text: str,
    cleaners: Optional[Sequence[HeadingCleaner]] = None,
) -> List[Heading]:
    """
    Executa sequencialmente a pipeline de cleaners funcionais nos headings.
    """
    if cleaners is None:
        cleaners = get_default_heading_cleaners()

    current_headings = headings
    for cleaner in cleaners:
        current_headings = cleaner(current_headings, full_text)

    return current_headings


def find_page_for_line(
    line_number: int, page_map: Optional[List[Dict[str, Any]]] = None
) -> Optional[int]:
    """
    Encontra a página (0-based) para a linha informada.
    """
    if not page_map:
        return None
    for p in page_map:
        if p['start_line'] <= line_number <= p['end_line']:
            return p['page']
    for p in reversed(page_map):
        if line_number >= p['start_line']:
            return p['page']
    return page_map[0]['page'] if page_map else None


def parse_headings_from_markdown(
    content: str, page_map: Optional[List[Dict[str, Any]]] = None
) -> List[Heading]:
    """
    Identifica todos os cabeçalhos ('#') com linha e página associada.
    """
    headings: List[Heading] = []
    lines = content.splitlines()

    for line_idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        match = HEADING_PATTERN.match(stripped)
        if match:
            hashes, title = match.groups()
            page = find_page_for_line(line_idx, page_map)
            headings.append(
                Heading(
                    line_number=line_idx,
                    level=len(hashes),
                    title=title.strip(),
                    raw=stripped,
                    page=page,
                )
            )

    return headings


def compute_line_starts(full_text: str) -> List[int]:
    """
    Offset cumulativo de início de cada linha.
    """
    starts: List[int] = []
    offset = 0
    for line in full_text.splitlines(keepends=True):
        starts.append(offset)
        offset += len(line)
    starts.append(offset)
    return starts


def content_char_range(
    full_text: str, line_starts: List[int], start_line: int, end_line: int
) -> Tuple[int, int]:
    """
    Offsets absolutos [start, end) do conteúdo no markdown consolidado.
    """
    last = len(line_starts) - 1
    region_start = line_starts[min(start_line, last)]
    region_end = line_starts[min(max(end_line, start_line), last)]
    region = full_text[region_start:region_end]
    begin = region_start + (len(region) - len(region.lstrip()))
    end = region_start + len(region.rstrip())
    return begin, max(begin, end)


MIN_PREAMBLE_CHARS = 10


def build_section_tree(  # noqa: PLR0914
    headings: List[Heading], full_text: str
) -> List[Section]:
    """
    Constrói a árvore hierárquica de Seções a partir dos headings e do texto.
    """
    if not headings:
        clean = full_text.strip()
        if clean:
            return [
                Section(
                    heading=Heading(
                        line_number=1,
                        level=1,
                        title='Documento',
                        raw='# Documento',
                        page=0,
                        level_source='fallback',
                    ),
                    breadcrumb=['Documento'],
                    content=clean,
                    role=SectionRole.UNKNOWN,
                    char_start=0,
                    char_end=len(full_text),
                    heading_char_start=0,
                )
            ]
        return []

    lines = full_text.splitlines()
    total_lines_count = len(lines)
    sliced: List[Tuple[Heading, str]] = []

    for i, h in enumerate(headings):
        start_line = h.line_number
        end_line = (
            headings[i + 1].line_number - 1
            if i + 1 < len(headings)
            else total_lines_count
        )
        content_lines = lines[start_line:end_line]
        content_text = '\n'.join(content_lines).strip()
        sliced.append((h, content_text))

    line_starts = compute_line_starts(full_text)
    total_lines = len(line_starts) - 1
    root_sections: List[Section] = []
    stack: List[Tuple[int, Section]] = []

    first_h_start = line_starts[min(headings[0].line_number - 1, total_lines)]
    if first_h_start > 0:
        pre_text = full_text[:first_h_start].strip()
        if len(pre_text) >= MIN_PREAMBLE_CHARS:
            pre_sec = Section(
                heading=Heading(
                    line_number=1,
                    level=1,
                    title='Preâmbulo',
                    raw='# Preâmbulo',
                    page=headings[0].page,
                    level_source='fallback',
                ),
                breadcrumb=['Preâmbulo'],
                content=pre_text,
                role=SectionRole.TITLE_BLOCK,
                char_start=0,
                char_end=first_h_start,
                heading_char_start=0,
            )
            root_sections.append(pre_sec)

    for idx, (heading, content) in enumerate(sliced):
        end_line = (
            headings[idx + 1].line_number - 1
            if idx + 1 < len(headings)
            else total_lines
        )
        char_start, char_end = content_char_range(
            full_text, line_starts, heading.line_number, end_line
        )

        while stack and stack[-1][0] >= heading.level:
            stack.pop()

        parent_section = stack[-1][1] if stack else None
        breadcrumb = [p.heading.title for _, p in stack] + [heading.title]

        current_section = Section(
            heading=heading,
            breadcrumb=breadcrumb,
            content=content,
            parent_title=(
                parent_section.heading.title if parent_section else None
            ),
            char_start=char_start,
            char_end=char_end,
            heading_char_start=line_starts[
                min(heading.line_number - 1, total_lines)
            ],
        )

        if parent_section:
            parent_section.children.append(current_section)
        else:
            root_sections.append(current_section)

        stack.append((heading.level, current_section))

    return root_sections


def flatten_sections(sections: List[Section]) -> List[Section]:
    """
    Retorna todas as seções da árvore em lista plana (ordem de leitura).
    """
    flat: List[Section] = []

    def walk(sec: Section) -> None:
        flat.append(sec)
        for child in sec.children:
            walk(child)

    for sec in sections:
        walk(sec)

    return flat


def tree_to_dict(sections: List[Section]) -> List[Dict[str, Any]]:
    """
    Serializa árvore de seções para dicionários serializáveis.
    """

    def sec_dict(s: Section) -> Dict[str, Any]:
        return {
            'title': s.title,
            'role': s.role.value if hasattr(s.role, 'value') else str(s.role),
            'role_confidence': s.role_confidence,
            'level': s.level,
            'level_source': s.heading.level_source,
            'char_start': s.char_start,
            'char_end': s.char_end,
            'children': [sec_dict(c) for c in s.children],
        }

    return [sec_dict(s) for s in sections]


def normalize_title_for_alias(title: str) -> str:
    """
    Remove pontuações e numeração de outline para casamento de aliases.
    """
    cleaned = strip_markup(title)
    cleaned = re.sub(r'^\d+[\.\d*]*\s*[-–:]?\s*', '', cleaned)
    cleaned = re.sub(r'[:\.\-_]+$', '', cleaned)
    return cleaned.strip().lower()


class RoleClassifier(ABC):
    @abstractmethod
    def classify(self, sections: List[Section]) -> List[Section]:
        pass


class AliasRoleClassifier(RoleClassifier):
    """
    Camada 1: Classificação determinística baseada em regex de aliases.
    """

    def __init__(self, aliases: Optional[Dict[SectionRole, List[str]]] = None):
        self.aliases = aliases or ROLE_ALIASES

    def classify(self, sections: List[Section]) -> List[Section]:
        for s in sections:
            if s.role and s.role != SectionRole.UNKNOWN:
                continue

            normalized_title = normalize_title_for_alias(s.title)

            for role, patterns in self.aliases.items():
                if any(
                    re.search(p, normalized_title, re.IGNORECASE)
                    or re.search(p, s.title.strip().lower(), re.IGNORECASE)
                    for p in patterns
                ):
                    s.role = role
                    s.role_confidence = 'alias_match'
                    break

        return sections


class PositionalAbstractFallbackClassifier(RoleClassifier):
    """
    Camada 2: Fallback posicional para Abstract ausente de cabeçalho explícito.
    """

    def classify(  # noqa: PLR6301
        self, sections: List[Section]
    ) -> List[Section]:
        has_abstract = any(s.role == SectionRole.ABSTRACT for s in sections)
        if has_abstract:
            return sections

        for idx, s in enumerate(sections):
            if s.role == SectionRole.INTRODUCTION and idx > 0:
                target = sections[idx - 1]
                if not target.role or target.role == SectionRole.UNKNOWN:
                    target.role = SectionRole.ABSTRACT
                    target.role_confidence = 'positional_fallback'

                    if idx - 1 > 0:
                        prev = sections[idx - 2]
                        if not prev.role or prev.role == SectionRole.UNKNOWN:
                            prev.role = SectionRole.TITLE_BLOCK
                            prev.role_confidence = 'positional_header'
                break

        return sections


def classify_section_roles(
    sections: List[Section],
    classifiers: Optional[Sequence[RoleClassifier]] = None,
) -> List[Section]:
    """
    Executa a sequência de classificadores de papéis semânticos.
    """
    if classifiers is None:
        classifiers = [
            AliasRoleClassifier(),
            PositionalAbstractFallbackClassifier(),
        ]

    current = sections
    for clf in classifiers:
        current = clf.classify(current)

    return current


def build_sections_tree_from_markdown(
    full_markdown: str,
    page_map: Optional[List[Dict[str, Any]]] = None,
) -> List[Section]:
    """
    Executa o Estágio 2 completo em memória:
    Parsing de headings -> Cleaners -> Árvore -> Classificação de papéis.
    """
    raw_headings = parse_headings_from_markdown(full_markdown, page_map)
    clean_headings = run_heading_pipeline(raw_headings, full_markdown)
    tree = build_section_tree(clean_headings, full_markdown)
    flat_sections = flatten_sections(tree)
    classify_section_roles(flat_sections)
    return tree


async def assign_sections_with_telemetry(
    chunks: List[Document],
    model: Optional[BaseChatModel] = None,
    run_id: Optional[UUID] = None,
) -> List[Document]:
    """
    Compatibilidade de pipeline/telemetria para o estágio de seções.
    """
    run_logger = get_run_logger()
    t_sec = datetime.now()
    if run_id:
        await run_logger.start_stage(run_id=run_id, stage='sections')

    sections_meta: Dict[str, Any] = {
        'input_window_text': '',
        'sections_detected': [],
        'mapping_success_rate': 1.0,
        'default_assigned': None,
    }

    seen_titles = set()
    for chunk in chunks:
        title = chunk.metadata.get('section_title', DEFAULT_SECTION_TITLE)
        role = chunk.metadata.get('section_role', 'unknown')
        conf = chunk.metadata.get('role_confidence', 'default')
        lvl = chunk.metadata.get('section_level', 1)
        if title not in seen_titles:
            sections_meta['sections_detected'].append({
                'section_name': title,
                'role': role,
                'role_confidence': conf,
                'level': lvl,
            })
            seen_titles.add(title)

    if run_id:
        d_sec = int((datetime.now() - t_sec).total_seconds() * 1000)
        await run_logger.complete_stage(
            run_id=run_id,
            stage='sections',
            duration_ms=d_sec,
            item_count=len(sections_meta['sections_detected']),
            data=sections_meta,
        )

    return chunks


# Stubs legados para compatibilidade reversa estrita
def detect_sections_with_model(
    documents: List[Document], model: Optional[BaseChatModel] = None
) -> Tuple[List[Dict[str, Any]], str]:
    return [], ''


def normalize_with_mapping(text: str) -> Tuple[str, List[int]]:
    return text.lower(), list(range(len(text)))


def assign_sections_to_chunks(
    chunks: List[Document], model: Optional[BaseChatModel] = None
) -> Tuple[List[Document], Dict[str, Any]]:
    for chunk in chunks:
        chunk.metadata.setdefault('section_title', DEFAULT_SECTION_TITLE)
        if not chunk.page_content.startswith('SECTION:'):
            chunk.page_content = (
                f'SECTION: {chunk.metadata["section_title"]}\n\n'
                f'{chunk.page_content}'
            )

    meta: Dict[str, Any] = {
        'input_window_text': '',
        'sections_detected': [],
        'mapping_success_rate': 1.0,
        'default_assigned': DEFAULT_SECTION_TITLE,
    }
    return chunks, meta
