from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from lumina.models import Typification
from lumina.schemas.typification import TypificationCreate
from lumina.services.typification_service import create_typification


@pytest.mark.asyncio
async def test_create_typification_success():
    session = AsyncMock()
    user_id = uuid4()
    data = TypificationCreate(name='Nova Tipificacao', source_ids=[])

    with (
        patch(
            'lumina.services.typification_service.typification_repo.get_by_name',
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            'lumina.services.typification_service.typification_repo.add_typification'
        ),
        patch(
            'lumina.services.typification_service.audit_service.register_action',
            new_callable=AsyncMock,
        ),
    ):
        result = await create_typification(session, user_id, data)
        assert result.name == 'Nova Tipificacao'


@pytest.mark.asyncio
async def test_create_typification_conflict():
    session = AsyncMock()
    user_id = uuid4()
    data = TypificationCreate(name='Nova Tipificacao', source_ids=[])

    with patch(
        'lumina.services.typification_service.typification_repo.get_by_name',
        new_callable=AsyncMock,
        return_value=Typification(name='Nova Tipificacao'),
    ):
        with pytest.raises(HTTPException) as exc:
            await create_typification(session, user_id, data)
        assert exc.value.status_code == 409
