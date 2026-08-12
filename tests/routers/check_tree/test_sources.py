from http import HTTPStatus
import pytest
from tests.factories.source_factory import SourceFactory

def test_create_source_api(client, token):
    response = client.post(
        "/source",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "API Source", "description": "API Description"}
    )
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["name"] == "API Source"

def test_get_sources_api(client, token):
    response = client.get(
        "/source",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == HTTPStatus.OK
    assert "sources" in response.json()
