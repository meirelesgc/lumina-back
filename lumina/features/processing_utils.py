# Utilitários de processamento assíncrono em background para conformidades de template e ABNT.

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

DEFAULT_ARTICLE_FILENAME = 'artigo.pdf'


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_upload(directory: Path, filename: str, content: bytes) -> tuple[Path, str]:
    suffix_name = Path(filename).name or DEFAULT_ARTICLE_FILENAME
    unique_filename = f'{uuid4()}_{suffix_name}'
    path = directory / unique_filename
    path.write_bytes(content)
    return path, unique_filename
