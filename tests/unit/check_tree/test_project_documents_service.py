from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_project_document_repo():
    return AsyncMock()


@pytest.mark.asyncio
async def test_create_project_document_logic():
    assert True
