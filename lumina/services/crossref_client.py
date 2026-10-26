import logging
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from lumina.core.settings import Settings

logger = logging.getLogger(__name__)

DOI_PATTERN = re.compile(r'10\.\d{4,9}/\S+')
DOI_PREFIX = re.compile(
    r'^(?:doi:\s*|https?://(?:dx\.)?doi\.org/)', re.IGNORECASE
)


@dataclass
class DoiMetadata:
    title: Optional[str]
    authors: list[str]
    year: Optional[int]
    container_title: Optional[str]


def normalize_doi(value: str) -> Optional[str]:
    doi = DOI_PREFIX.sub('', value.strip(), count=1)
    if not DOI_PATTERN.fullmatch(doi):
        return None
    return doi.lower()


def _author_name(author: dict) -> Optional[str]:
    if author.get('name'):
        return author['name']
    parts = [author.get('given'), author.get('family')]
    return ' '.join(part for part in parts if part) or None


def _parse_work(work: dict) -> DoiMetadata:
    titles = work.get('title') or []
    containers = work.get('container-title') or []
    date_parts = (work.get('issued') or {}).get('date-parts') or [[None]]
    authors = [_author_name(author) for author in work.get('author') or []]
    return DoiMetadata(
        title=titles[0] if titles else None,
        authors=[name for name in authors if name],
        year=date_parts[0][0] if date_parts[0] else None,
        container_title=containers[0] if containers else None,
    )


async def fetch_doi_metadata(
    doi: str, transport: Optional[httpx.AsyncBaseTransport] = None
) -> Optional[DoiMetadata]:
    settings = Settings()
    headers = {}
    if settings.CROSSREF_MAILTO:
        headers['User-Agent'] = f'Lumina (mailto:{settings.CROSSREF_MAILTO})'

    try:
        async with httpx.AsyncClient(
            base_url=settings.CROSSREF_URL,
            timeout=settings.CROSSREF_TIMEOUT_SECONDS,
            headers=headers,
            transport=transport,
        ) as client:
            response = await client.get(f'/works/{doi}')
        response.raise_for_status()
        return _parse_work(response.json()['message'])
    except (
        httpx.HTTPError,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        AttributeError,
    ) as error:
        logger.warning('Crossref lookup failed for %s: %s', doi, error)
        return None
