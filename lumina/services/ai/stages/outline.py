from dataclasses import dataclass
from itertools import groupby
from typing import List

from langchain_core.documents import Document

PREVIEW_CHARS = 200
CHARS_PER_TOKEN = 4
PATH_SEPARATOR = ' > '


@dataclass(frozen=True)
class OutlineSection:
    """
    Seção do sumário do documento: os chunks da ingestão que pertencem a uma
    mesma seção, na ordem de leitura.
    """

    id: str
    index: int
    title: str
    path: str
    first_page: int
    last_page: int
    chunks: tuple[Document, ...]

    @property
    def depth(self) -> int:
        return self.path.count(PATH_SEPARATOR)

    @property
    def text(self) -> str:
        return '\n'.join(chunk_body(c) for c in self.chunks)

    @property
    def tokens(self) -> int:
        return len(self.text) // CHARS_PER_TOKEN

    @property
    def preview(self) -> str:
        return ' '.join(self.text.split())[:PREVIEW_CHARS].rstrip()


def chunk_body(chunk: Document) -> str:
    """Texto do chunk sem o prefixo `[título]` que o fatiamento acrescenta."""
    prefix = f'[{chunk.metadata.get("section_title", "")}] '
    return chunk.page_content.removeprefix(prefix)


def section_id(section_index: int) -> str:
    return f's{section_index + 1:02d}'


def build_outline(chunks: List[Document]) -> List[OutlineSection]:
    """
    Agrupa os chunks por seção, na ordem de leitura do documento. Páginas
    são contadas a partir de 1, como no sumário que o seletor recebe.
    """

    def order(chunk: Document) -> tuple[int, int, int]:
        meta = chunk.metadata
        return (
            meta['section_index'],
            meta['page'],
            meta.get('chunk_index_in_section', 0),
        )

    ordered = sorted(chunks, key=order)
    outline = []
    for index, group in groupby(
        ordered, key=lambda c: c.metadata['section_index']
    ):
        members = tuple(group)
        pages = [c.metadata['page'] + 1 for c in members]
        outline.append(
            OutlineSection(
                id=section_id(index),
                index=index,
                title=members[0].metadata.get('section_title', ''),
                path=members[0].metadata.get('section_path', ''),
                first_page=min(pages),
                last_page=max(pages),
                chunks=members,
            )
        )
    return outline


def page_range(section: OutlineSection) -> str:
    if section.first_page == section.last_page:
        return f'p{section.first_page}'
    return f'p{section.first_page}–p{section.last_page}'


def outline_markdown(outline: List[OutlineSection]) -> str:
    """
    Sumário em Markdown, indentado pela profundidade do caminho de títulos,
    com id, páginas, tokens estimados e o começo do texto de cada seção.
    """
    lines = []
    for section in outline:
        indent = '  ' * section.depth
        lines.append(
            f'{indent}- [{section.id}] {section.title} · '
            f'{page_range(section)} · ~{section.tokens} tokens'
        )
        lines.append(f'{indent}  "{section.preview}"')
    return '\n'.join(lines)
