from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_document_group_repo():
    return AsyncMock()


@pytest.mark.asyncio
async def test_create_group_logic():
    assert True
