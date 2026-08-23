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
        return self._cache.get(key)

    def list_keys(self) -> list[str]:
        return list(self._cache.keys())

    def list_all(self) -> list[dict[str, Any]]:
        return list(self._cache.values())

    def list_by_doc_id(self, doc_id: str) -> list[dict[str, Any]]:
        results = [
            item for item in self._cache.values() if item.get('doc_id') == doc_id
        ]
        results.sort(key=lambda item: item.get('created_at') or '')
        return results

    def save(self, key: str, data: dict[str, Any]) -> Path:
        path = self._path_for(key)
        with self._lock:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._cache[key] = data
        return path
