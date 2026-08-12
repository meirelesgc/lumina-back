from http import HTTPStatus
import pytest

@pytest.mark.asyncio
async def test_read_project_documents_unauthorized(client):
    response = client.post(
        '/project-document', json={}
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
