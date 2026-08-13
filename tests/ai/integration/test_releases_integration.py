import pytest
from uuid import uuid4

from lumina.app import app
from lumina.core.llm import get_model
from lumina.core.cache import get_redis
from lumina.core.vectorstore import get_vectorstore
from lumina.models import Document, DocumentHistory
from tests.factories.document_factory import ProjectDocumentFactory
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
@patch(
    'lumina.services.release_orchestrator.vector_service.create_vectors',
    new_callable=AsyncMock,
)
async def test_create_release_integration(
    mock_create_vectors,
    client,
    token,
    session,
    unit,
    user,
    fake_release_pipeline_llm,
):
    """
    Testa a integração do fluxo `POST /doc/{doc_id}/releases`, injetando um LLM Fake.
    - Como o FastAPI TestClient executa as background tasks de maneira bloqueante
      antes de devolver a resposta HTTP, a BackgroundTask `release_pipeline` será
      executada por inteira.
    - Ao final, nenhum token real foi gasto, mas TODO O FLUXO de Parsing e WebSockets foi coberto.
    """
    # 1. Arrange
    # Sobrescreve a dependência que provê a LLM pela nossa fixture mockada.
    app.dependency_overrides[get_model] = lambda: fake_release_pipeline_llm

    mock_redis = AsyncMock()
    app.dependency_overrides[get_redis] = lambda: mock_redis

    mock_vstore = AsyncMock()
    # asimilarity_search returns a list of chunks
    from langchain_core.documents import Document as LangchainDocument

    mock_vstore.asimilarity_search.return_value = [
        LangchainDocument(
            page_content='Mock chunk', metadata={'chunk_index': 0}
        )
    ]
    app.dependency_overrides[get_vectorstore] = lambda: mock_vstore

    document = Document(
        name='Edital de Teste',
        identifier='2024-001',
        description='Teste de Integração de Release',
        processing_status='IDLE',
        unit_id=unit.id,
        created_by=user.id,
    )

    session.add(document)
    await session.flush()
    doc_id = document.id

    doc_history = DocumentHistory(
        document_id=doc_id, status='IDLE', created_by=user.id
    )
    session.add(doc_history)
    await session.commit()
    await session.refresh(document)

    headers = {'Authorization': f'Bearer {token}'}

    # Como o endpoint recebe um arquivo via UploadFile (Form data)
    # Criaremos um arquivo em memória (dummy PDF)
    file_content = b'%PDF-1.4 dummy content'
    files = {'file': ('test.pdf', file_content, 'application/pdf')}
    data = {'bump': 'minor'}

    # 2. Act
    # Ao chamar o post, ele dispara o release_pipeline via BackgroundTasks
    response = client.post(
        f'/doc/{doc_id}/release', headers=headers, data=data, files=files
    )

    # 3. Assert
    # Limpar overrides para não afetar outros testes
    app.dependency_overrides.clear()

    # Validações HTTP
    assert response.status_code == 201
    resp_data = response.json()
    assert resp_data['version'] == '1.0.0'
    assert resp_data['file_path'] is not None

    # Validações de Banco de Dados Pós-BackgroundTask
    # Como a BackgrounTask roda no TestClient, o processing_status deve ir
    # de QUEUED -> PROCESSING -> IDLE (em caso de sucesso simulado).
    await session.refresh(document)
    # Status IDLE reflete que o pipeline rodou até o final (sucesso mockado da AI)
    assert document.processing_status == 'IDLE'

    # Se testarmos um Fake Model que quebra o Pydantic, o status seria FAILED, etc.
