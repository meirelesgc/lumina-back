import json

import httpx
import pytest

from lumina.services.crossref_client import (
    DoiMetadata,
    fetch_doi_metadata,
    normalize_doi,
)

CROSSREF_WORK = {
    'status': 'ok',
    'message': {
        'DOI': '10.1590/s0102-311x2023000100001',
        'title': ['Saúde coletiva e pesquisa'],
        'author': [
            {'given': 'Ana', 'family': 'Souza'},
            {'family': 'Lima'},
            {'name': 'Grupo de Estudos'},
        ],
        'issued': {'date-parts': [[2023, 3, 1]]},
        'container-title': ['Cadernos de Saúde Pública'],
    },
}


@pytest.mark.parametrize(
    'raw',
    [
        '10.1590/S0102-311X2023000100001',
        'doi:10.1590/S0102-311X2023000100001',
        'DOI: 10.1590/S0102-311X2023000100001',
        'https://doi.org/10.1590/S0102-311X2023000100001',
        'https://dx.doi.org/10.1590/S0102-311X2023000100001',
        'HTTPS://DOI.ORG/10.1590/S0102-311X2023000100001',
        '  https://doi.org/10.1590/S0102-311X2023000100001  ',
    ],
)
def test_normalize_doi_strips_prefix_and_lowercases(raw):
    assert normalize_doi(raw) == '10.1590/s0102-311x2023000100001'


@pytest.mark.parametrize(
    'raw',
    [
        '',
        'abc',
        '11.1590/abc',
        '10.123/abc',
        '10.1234567890/abc',
        '10.1234/',
        '10.1234 abc',
        'https://example.org/10.1234/abc',
        'ftp://doi.org/10.1234/abc',
    ],
)
def test_normalize_doi_rejects_invalid_values(raw):
    assert normalize_doi(raw) is None


def _transport(handler):
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_fetch_doi_metadata_reads_crossref_work():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=CROSSREF_WORK)

    metadata = await fetch_doi_metadata(
        '10.1590/s0102-311x2023000100001', transport=_transport(handler)
    )

    assert metadata == DoiMetadata(
        title='Saúde coletiva e pesquisa',
        authors=['Ana Souza', 'Lima', 'Grupo de Estudos'],
        year=2023,
        container_title='Cadernos de Saúde Pública',
    )
    assert requests[0].url.path == ('/works/10.1590/s0102-311x2023000100001')


@pytest.mark.asyncio
async def test_fetch_doi_metadata_accepts_missing_optional_fields():
    work = {'message': {'title': ['Só o título']}}

    metadata = await fetch_doi_metadata(
        '10.1234/abc',
        transport=_transport(lambda request: httpx.Response(200, json=work)),
    )

    assert metadata == DoiMetadata(
        title='Só o título', authors=[], year=None, container_title=None
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'response',
    [
        httpx.Response(404, text='Resource not found.'),
        httpx.Response(500, text='boom'),
        httpx.Response(200, text='not json'),
        httpx.Response(200, json={'message': 'unexpected'}),
        httpx.Response(200, content=json.dumps([1, 2]).encode()),
    ],
    ids=['404', '500', 'texto', 'message_texto', 'lista'],
)
async def test_fetch_doi_metadata_returns_none_on_bad_response(response):
    metadata = await fetch_doi_metadata(
        '10.1234/abc', transport=_transport(lambda request: response)
    )

    assert metadata is None


@pytest.mark.asyncio
async def test_fetch_doi_metadata_returns_none_on_timeout():
    def handler(request):
        raise httpx.ReadTimeout('timeout', request=request)

    metadata = await fetch_doi_metadata(
        '10.1234/abc', transport=_transport(handler)
    )

    assert metadata is None
