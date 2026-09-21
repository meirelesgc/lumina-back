from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class SectionRole(str, Enum):
    TITLE_BLOCK = 'title_block'
    ABSTRACT = 'abstract'
    INTRODUCTION = 'introduction'
    METHODOLOGY = 'methodology'
    RESULTS = 'results'
    DISCUSSION = 'discussion'
    CONCLUSION = 'conclusion'
    REFERENCES = 'references'
    UNKNOWN = 'unknown'


@dataclass
class Heading:
    """
    Representa um cabecalho Markdown identificado no documento.
    """

    line_number: int
    level: int
    title: str
    raw: str
    page: Optional[int] = None
    level_source: str = 'font'


@dataclass
class Section:
    """
    Representa uma secao delimitada por cabecalho e conteudo associado.
    """

    heading: Heading
    breadcrumb: List[str] = field(default_factory=list)
    content: str = ''
    parent_title: Optional[str] = None
    children: List['Section'] = field(default_factory=list)
    role: SectionRole = SectionRole.UNKNOWN
    role_confidence: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    heading_char_start: Optional[int] = None

    @property
    def title(self) -> str:
        return self.heading.title

    @title.setter
    def title(self, value: str) -> None:
        self.heading.title = value

    @property
    def level(self) -> int:
        return self.heading.level

    @level.setter
    def level(self, value: int) -> None:
        self.heading.level = value
