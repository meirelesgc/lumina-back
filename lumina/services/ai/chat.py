import os
import re
from typing import Any, Dict, List
from uuid import UUID

from fastapi import HTTPException
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from lumina import prompts as PROMPTS
from lumina.core.dependencies import Model, VStore
from lumina.core.settings import Settings
from lumina.models import DocumentMessage
from lumina.repositories import chat_repo, doc_repo, release_repo
from lumina.schemas import DocumentMessageCreate
from lumina.schemas.ai import AnswerWithCitations
from lumina.services import branch_service, release_service
from lumina.services.ai import stages

CONTEXT_PATTERN = re.compile(r'<([^:]+):([^>]+)>')
MAX_FULL_TEXT_CHARS = 80000
SETTINGS = Settings()


async def build_branch_prompt(session: AsyncSession, branch_id: str) -> str:
    """
    Carrega regra normativa de um ramo e gera o bloco de contexto.
    """
    branch = await branch_service.get_branch_by_id(session, branch_id)
    return f"""
<CONTEXTO-BASE-CONHECIMENTO-BRANCH:{branch.id}>
**Item Avaliado:** {branch.taxonomy.typification.name}
**Tópico de Referência:** {branch.taxonomy.title}
**Pergunta de Verificação:** O conteúdo necessário está presente
**nos trechos recuperados** e cumpre integralmente os requisitos baseados em:
{branch.title}
{branch.description}
<CONTEXTO-BASE-CONHECIMENTO-BRANCH:{branch.id}>
"""


async def get_explicit_context(session: AsyncSession, msg: str) -> List[str]:
    """
    Detecta menções <branch:uuid> no texto e constrói prompts contextuais.
    """
    matches = CONTEXT_PATTERN.findall(msg)
    context = []
    for match_type, match_id in matches:
        if match_type == 'branch':
            prompt = await build_branch_prompt(session, match_id)
            context.append(prompt)
    return context


def build_chat_history_prompt(recent_messages: list[Any]) -> str:
    """
    Formata o histórico das mensagens recentes para inserção no prompt.
    """
    return '\n---\n'.join([
        f"""
QUEM FALOU:
{m.author.username}:
O QUE FALOU:
{m.content}
"""
        for m in recent_messages
    ])


async def get_document_auto_context(
    session: AsyncSession, doc_id: UUID
) -> List[str]:
    """
    Recupera os tópicos e perguntas normativas ativas no documento.
    """
    doc = await doc_repo.get_by_id(session, doc_id)
    if not doc or doc.deleted_at:
        return []

    prompts_list = []
    for typification in doc.typifications:
        if typification.deleted_at:
            continue
        for taxonomy in typification.taxonomies:
            if taxonomy.deleted_at:
                continue
            for branch in taxonomy.branches:
                if branch.deleted_at:
                    continue
                prompt = f"""
<CONTEXTO-BASE-CONHECIMENTO-BRANCH:{branch.id}>
**Item Avaliado:** {typification.name}
**Tópico de Referência:** {taxonomy.title}
**Pergunta de Verificação:** O conteúdo necessário está presente
**nos trechos recuperados** e cumpre integralmente os requisitos baseados em:
{branch.title}
{branch.description}
<CONTEXTO-BASE-CONHECIMENTO-BRANCH:{branch.id}>
"""
                prompts_list.append(prompt)
    return prompts_list


async def get_prompt_context(
    vstore: VStore, db_release: Any, msg: str
) -> tuple[List[str], List[Any]]:
    if not msg:
        return [], []

    base_filter = stages.retrieval.get_base_filter(db_release)
    original_chunks = await vstore.asimilarity_search(
        msg, k=5, filter=base_filter
    )
    if not original_chunks:
        return [], []

    return (
        stages.retrieval.build_chunk_prompts(original_chunks),
        original_chunks,
    )


async def create_ai_response(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    user_id: UUID,
    doc_id: UUID,
    data: DocumentMessageCreate,
    model: Model,
    vstore: VStore,
    recent_messages: list[DocumentMessage],
) -> Dict:
    """
    Gera a resposta do Chat RAG conversacional com resolução de coordenadas
    físicas (rects) para highlight no visualizador de PDF.
    """
    releases_list = await release_service.get_releases_by_document(
        session, doc_id
    )
    if not releases_list:
        raise HTTPException(
            status_code=400,
            detail='Nenhuma release encontrada para este documento.',
        )

    db_release = await release_service.get_release_with_details(
        session, releases_list[0].id
    )

    auto_prompts = await get_document_auto_context(session, doc_id)
    explicit_prompts = await get_explicit_context(session, data.content)

    b_prm, branch_chunks = await get_prompt_context(
        vstore, db_release, '\n---\n'.join(explicit_prompts)
    )

    m_prm, msg_chunks = await get_prompt_context(
        vstore, db_release, data.content
    )

    all_chunks = branch_chunks + msg_chunks
    context = '\n---\n'.join(m_prm + b_prm + auto_prompts + explicit_prompts)

    chat_context = build_chat_history_prompt(recent_messages)

    prompt = PROMPTS.CHAT.format(
        context=context,
        content=data.content,
        recent_messages=chat_context,
    )

    structured_model = model.with_structured_output(AnswerWithCitations)
    response: AnswerWithCitations = structured_model.invoke(prompt)

    resolved_citations = stages.citations.resolve_citations(
        response.citations, all_chunks
    )

    return {'answer': response.answer, 'references': resolved_citations}


async def _extract_document_text(file_path: str) -> str:
    """
    Extrai até 80.000 caracteres de texto bruto via PyMuPDF para o assistente.
    """
    loader = PyMuPDFLoader(file_path)
    raw_docs = loader.load()
    text = '\n\n'.join([d.page_content for d in raw_docs])
    if len(text) > MAX_FULL_TEXT_CHARS:
        text = text[-MAX_FULL_TEXT_CHARS:]
    return text


async def chat_with_document(  # noqa: PLR0913, PLR0917
    doc_id: str,
    message: str,
    history: list[dict],
    model: BaseChatModel,
    session: AsyncSession,
    conversation_id: str | None = None,
) -> dict:
    """
    Atua como assistente geral contínuo (OiacIA) sobre o texto do documento.
    """
    doc = await doc_repo.get_by_id(session, doc_id)
    if not doc or doc.deleted_at:
        raise HTTPException(status_code=404, detail='Documento não encontrado')

    document_text: str | None = None

    if conversation_id:
        conv = await chat_repo.get_conversation_by_id(session, conversation_id)
        if conv and conv.context_text:
            document_text = conv.context_text

    if document_text is None:
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

        document_text = await _extract_document_text(full_path)

        if conversation_id:
            await chat_repo.update_conversation_context(
                session, conversation_id, document_text
            )

    system_prompt = f"""Você é a OiacIA, assistente especializado em editais.

## Conteúdo do Documento
{document_text}

## Regras
- Responda APENAS com base no conteúdo do documento fornecido acima.
- Se não estiver no documento, diga que não encontrou a informação.
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
