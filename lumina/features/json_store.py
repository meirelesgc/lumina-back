# "Banco de dados" simplificado em JSON: cada resultado é um arquivo `<chave>.json`, cacheado em memória. Uma instância para template_conformity_service.py e outra para abnt_conformity_service.py.

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


class JsonResultStore:
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._cache: dict[str, dict[str, Any]] = {}
        self._load_all()

    def _path_for(self, key: str) -> Path:
        return self.directory / f'{key}.json'

    def _load_all(self) -> None:
        for path in self.directory.glob('*.json'):
            try:
                with open(path, encoding='utf-8') as f:
                    self._cache[path.stem] = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue

    def get(self, key: str) -> dict[str, Any] | None:
        item = self._cache.get(key)
        if item is None:
            return None
        return self._normalize(key, item)

    def list_keys(self) -> list[str]:
        return list(self._cache.keys())

    def list_all(self) -> list[dict[str, Any]]:
        return [self._normalize(key, item) for key, item in self._cache.items()]

    def list_by_doc_id(self, doc_id: str) -> list[dict[str, Any]]:
        results = [
            self._normalize(key, item)
            for key, item in self._cache.items()
            if item.get('doc_id') == doc_id
        ]
        results.sort(key=lambda item: item.get('created_at') or '', reverse=True)
        return results

    def _normalize(self, key: str, item: dict[str, Any]) -> dict[str, Any]:
        # Resultados gravados no formato antigo nao tinham id, file_path nem created_at.
        normalized = dict(item)
        normalized.setdefault('id', key)
        updated_at = normalized.get('updated_at') or ''
        normalized.setdefault('created_at', updated_at)
        if not normalized.get('file_path'):
            normalized['file_path'] = self._legacy_file_path(normalized)
        return normalized

    def _legacy_file_path(self, item: dict[str, Any]) -> str:
        metadata = ((item.get('report') or {}).get('metadata') or {})
        article_file = str(metadata.get('article_file') or '').replace('\\', '/')
        for marker in (
            'template_conformity/uploads/',
            'abnt_conformity/uploads/',
        ):
            index = article_file.find(marker)
            if index != -1:
                return article_file[index:]
        doc_id = item.get('doc_id') or ''
        if not doc_id:
            return ''
        feature_dir = self.directory.parent.name
        return f'{feature_dir}/uploads/{doc_id}.pdf'

    def save(self, key: str, data: dict[str, Any]) -> Path:
        path = self._path_for(key)
        with self._lock:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._cache[key] = data
        return path
