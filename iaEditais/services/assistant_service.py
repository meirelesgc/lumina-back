import os

from fastapi import HTTPException
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.core.settings import Settings
from iaEditais.repositories import doc_repo, release_repo

SETTINGS = Settings()


async def chat_with_document(
    doc_id: str,
    message: str,
    history: list[dict],
    model: BaseChatModel,
    session: AsyncSession,
) -> dict:
    doc = await doc_repo.get_by_id(session, doc_id)
    if not doc or doc.deleted_at:
        raise HTTPException(status_code=404, detail='Documento não encontrado')

    releases = await release_repo.get_releases_by_document(session, doc_id)
    if not releases:
        raise HTTPException(
            status_code=400,
            detail='Nenhum arquivo enviado para este documento',
        )

    latest = releases[0]
    if not latest.file_path:
        raise HTTPException(
            status_code=400,
            detail='Nenhum arquivo enviado para este documento',
        )

    filename = latest.file_path.split('/')[-1]
    full_path = os.path.join(SETTINGS.UPLOAD_DIRECTORY, filename)

    if not os.path.exists(full_path):
        raise HTTPException(
            status_code=404, detail='Arquivo não encontrado no servidor'
        )

    loader = PyMuPDFLoader(full_path)
    raw_docs = loader.load()
    document_text = '\n\n'.join(
        [d.page_content for d in raw_docs]
    )

    max_chars = 80000
    if len(document_text) > max_chars:
        document_text = document_text[-max_chars:]

    system_prompt = f"""Você é a OiacIA, assistente especializado em análise de documentos de licitação e editais.

## Conteúdo do Documento
{document_text}

## Regras
- Responda APENAS com base no conteúdo do documento fornecido acima.
- Se a resposta não estiver no documento, diga claramente que não encontrou essa informação.
- Seja conciso e objetivo.
- Responda em português."""

    messages = [{'role': 'system', 'content': system_prompt}]

    for msg in history[-10:]:
        messages.append({'role': msg['role'], 'content': msg['content']})

    messages.append({'role': 'user', 'content': message})

    try:
        response = await model.ainvoke(messages)
        return {'response': response.content}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Erro ao gerar resposta: {str(e)}',
        )
