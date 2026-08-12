import pytest
from tests.factories.typification_factory import TypificationFactory

def test_create_typification_endpoint(client, token):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": "API Typification",
        "source_ids": []
    }
    
    response = client.post("/typification", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "API Typification"

@pytest.mark.asyncio
async def test_get_typifications_endpoint(client, token, session):
    headers = {"Authorization": f"Bearer {token}"}
    
    typ = TypificationFactory(name="API Get Typification")
    session.add(typ)
    await session.commit()
    
    response = client.get("/typification", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "typifications" in data
    assert len(data["typifications"]) >= 1
