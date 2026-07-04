import os
import re
from collections import defaultdict
from typing import Any, List
from uuid import UUID

from langchain_community.document_loaders import PyMuPDFLoader
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais import prompts as PROMPTS
from iaEditais.core.dependencies import Model, VStore
from iaEditais.core.settings import Settings
from iaEditais.models import DocumentMessage, DocumentRelease
from iaEditais.repositories import doc_repo
from iaEditais.schemas import DocumentMessageCreate
from iaEditais.services import (
    branch_service,
    release_logic_service,
    release_service,
)

MAX_CHUNKS = 2
MAX_FULL_TEXT_CHARS = 80000
CONTEXT_PATTERN = re.compile(r'<([^:]+):([^>]+)>')
SETTINGS = Settings()


def get_base_filter(db_release: DocumentRelease) -> dict:
    path = db_release.file_path.split('/')[-1]
    allowed_source = f'iaEditais/storage/uploads/{path}'
    return {'source': allowed_source}


async def _load_document_text(db_release: DocumentRelease) -> str | None:
    filename = db_release.file_path.split('/')[-1]
    full_path = os.path.join(SETTINGS.UPLOAD_DIRECTORY, filename)

    if not os.path.exists(full_path):
        return None

    try:
        loader = PyMuPDFLoader(full_path)
        raw_docs = loader.load()
        text = '\n\n'.join([d.page_content for d in raw_docs])
        if len(text) > MAX_FULL_TEXT_CHARS:
            text = text[-MAX_FULL_TEXT_CHARS:]
        return text
    except Exception:
        return None


async def build_branch_prompt(session: AsyncSession, branch_id: str) -> str:
    branch = await branch_service.get_branch_by_id(session, branch_id)
    return f"""
<CONTEXTO-BASE-CONHECIMENTO-BRANCH:{branch.id}>
**Item Avaliado:** {branch.taxonomy.typification.name}
**Tópico de Referência:** {branch.taxonomy.title}
**Pergunta de Verificação:** O conteúdo necessário está presente **nos trechos recuperados** e cumpre integralmente o requisitos baseados em:
{branch.title}
{branch.description}
<CONTEXTO-BASE-CONHECIMENTO-BRANCH:{branch.id}>
"""


async def get_context(session: AsyncSession, msg: str) -> List[str]:
    matches = CONTEXT_PATTERN.findall(msg)
    context = []

    for match_type, match_id in matches:
        if match_type == 'branch':
            prompt = await build_branch_prompt(session, match_id)
            context.append(prompt)
        elif match_type != 'ai':
            print(f'Unknown type: {match_type}')

    return context


def build_chunk_prompts(chunks: List) -> List[str]:
    grupos = defaultdict(list)

    for chunk in chunks:
        titulo = chunk.metadata.get('section_title', '')
        conteudo = chunk.page_content

        if '\n\n' in conteudo:
            conteudo = conteudo.split('\n\n', 1)[1]

        grupos[titulo].append(conteudo.strip())

    prompts_list = []

    for titulo, conteudos in grupos.items():
        prompt = f'SECTION: {titulo}\n\n' + '\n\n---\n\n'.join(conteudos)
        prompts_list.append(prompt)

    return prompts_list


async def get_prompt_context(
    vstore: VStore, db_release: DocumentRelease, msg: str
) -> List[str]:
    if not msg:
        return []

    base_filter = get_base_filter(db_release)
    original_chunks = await vstore.asimilarity_search(
        msg, k=MAX_CHUNKS, filter=base_filter
    )

    if not original_chunks:
        return []

    expanded_chunks = await release_logic_service.get_expanded_chunks(
        vstore, original_chunks
    )

    return build_chunk_prompts(expanded_chunks)


def build_chat_prompt(recent_messages: list[Any]) -> str:
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
**Pergunta de Verificação:** O conteúdo necessário está presente **nos trechos recuperados** e cumpre integralmente o requisitos baseados em:
{branch.title}
{branch.description}
<CONTEXTO-BASE-CONHECIMENTO-BRANCH:{branch.id}>
"""
                prompts_list.append(prompt)
    return prompts_list


async def create_ai_response(
    session: AsyncSession,
    user_id: UUID,
    doc_id: UUID,
    data: DocumentMessageCreate,
    model: Model,
    vstore: VStore,
    recent_messages: list[DocumentMessage],
) -> str:
    releases_list = await release_service.get_releases_by_document(
        session, doc_id
    )
    db_release = await release_service.get_release_with_details(
        session, releases_list[0].id
    )

    auto_prompts = await get_document_auto_context(session, doc_id)
    explicit_prompts = await get_context(session, data.content)

    branch_context = await get_prompt_context(
        vstore, db_release, '\n---\n'.join(explicit_prompts)
    )

    msg_context = await get_prompt_context(vstore, db_release, data.content)
    context = '\n---\n'.join(msg_context + branch_context + auto_prompts + explicit_prompts)

    chat_context = build_chat_prompt(recent_messages)

    full_text = await _load_document_text(db_release)
    if full_text:
        context = f"<CONTEUDO-COMPLETO-DO-DOCUMENTO>\n{full_text}\n</CONTEUDO-COMPLETO-DO-DOCUMENTO>\n\n---\n\n{context}"

    prompt = PROMPTS.CHAT.format(
        context=context,
        content=data.content,
        recent_messages=chat_context,
    )
    response = model.invoke(prompt)
    return response.content
