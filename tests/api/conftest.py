import pytest

from lumina.services.crossref_client import DoiMetadata


class CrossrefStub:
    """Substitui o Crossref: devolve os metadados cadastrados por DOI.

    DOI sem cadastro se comporta como Crossref fora do ar (`None`).
    `calls` guarda os DOIs consultados, na ordem.
    """

    def __init__(self):
        self.works: dict[str, DoiMetadata] = {}
        self.calls: list[str] = []

    async def __call__(self, doi, transport=None):
        self.calls.append(doi)
        return self.works.get(doi)


@pytest.fixture
def crossref(monkeypatch):
    stub = CrossrefStub()
    monkeypatch.setattr(
        'lumina.services.crossref_client.fetch_doi_metadata', stub
    )
    return stub
