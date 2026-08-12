# "Banco de dados" simplificado em JSON: cada resultado é um arquivo
# `<chave>.json` dentro de uma pasta dedicada. Os arquivos existentes são
# carregados em memória na inicialização; leituras usam o cache e escritas
# atualizam o arquivo em disco e o cache, mantendo os dois sempre em sincronia.
#
# Usado tanto para os resultados de conformidade com template quanto para os
# de conformidade ABNT (uma instância para cada, ver service.py) -- os dois
# JSONs resultantes têm formatos diferentes, mas a persistência é a mesma.

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

    def save(self, key: str, data: dict[str, Any]) -> Path:
        path = self._path_for(key)
        with self._lock:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._cache[key] = data
        return path
