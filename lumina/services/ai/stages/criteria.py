from typing import Any, Iterator, List

from langchain_core.documents import Document

from lumina.models import Typification
from lumina.schemas.typification import TypificationList


def iter_tree_branches(
    tree: List[Typification] | List[dict],
) -> Iterator[tuple[dict, dict]]:
    """
    Percorre a árvore normativa e devolve pares (taxonomia, ramo) já
    serializados, na ordem de tipificação, taxonomia e ramo.
    """
    serialized = TypificationList.model_validate({
        'typifications': tree
    }).model_dump(mode='json')
    for typification in serialized['typifications']:
        for taxonomy in typification.get('taxonomies') or []:
            for branch in taxonomy.get('branches') or []:
                yield taxonomy, branch


def source_names(taxonomy: dict) -> str:
    return ', '.join([
        s.get('name', '')
        if isinstance(s, dict)
        else getattr(s, 'name', str(s))
        for s in taxonomy.get('sources') or []
    ])


def criteria_fields(taxonomy: dict, branch: dict) -> dict[str, Any]:
    """
    Campos do critério que o prompt de avaliação e o snapshot leem, comuns a
    qualquer forma de montar o contexto.
    """
    taxonomy_title = (taxonomy.get('title') or '').strip()
    title = (branch.get('title') or '').strip()
    description = (branch.get('description') or '').strip()
    return {
        'id': branch.get('id'),
        'source': source_names(taxonomy),
        'requirement': (
            f'{title}: {description}'
            if title and description
            else (title or description)
        ),
        'expected_section': taxonomy_title,
        'query': f"Analise o item '{title}' na seção '{taxonomy_title}'.",
    }


def merge_presidio_mappings(chunks: List[Document]) -> dict:
    """Junta os mapas de reversão do Presidio dos chunks enviados."""
    merged: dict = {}
    for chunk in chunks:
        mapping = chunk.metadata.get('presidio_mapping') or {}
        for category, entities in mapping.items():
            merged.setdefault(category, {}).update(entities)
    return merged
