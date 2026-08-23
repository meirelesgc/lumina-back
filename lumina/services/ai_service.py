import os
import re
from typing import Any, Dict, List
from uuid import UUID

from langchain_community.document_loaders import PyMuPDFLoader
from sqlalchemy.ext.asyncio import AsyncSession

from lumina import prompts as PROMPTS
from lumina.core.dependencies import Model, VStore
from lumina.core.settings import Settings
from lumina.models import DocumentMessage, DocumentRelease
from lumina.repositories import doc_repo
from lumina.schemas import DocumentMessageCreate
from lumina.schemas.ai import AnswerWithCitations, Citation
from lumina.services import (
    branch_service,
    release_logic_service,
    release_service,
)

MAX_CHUNKS = 5  # increased chunks for better RAG since chunks are now smaller (max 500 chars)
MAX_FULL_TEXT_CHARS = 80000
CONTEXT_PATTERN = re.compile(r'<([^:]+):([^>]+)>')
SETTINGS = Settings()


def get_base_filter(db_release: DocumentRelease) -> dict:
    path = db_release.file_path.split('/')[-1]
    allowed_source = f'lumina/storage/uploads/{path}'
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
    prompts_list = []

    for chunk in chunks:
        chunk_id = chunk.metadata.get('chunk_id', 'unknown_id')
        section = chunk.metadata.get('section_title', '')
        conteudo = chunk.page_content

        if '\n\n' in conteudo and conteudo.startswith('SECTION:'):
            conteudo = conteudo.split('\n\n', 1)[1]

        prompt = f'[FONTE] chunk_id: {chunk_id}\nSECTION: {section}\n{conteudo.strip()}'
        prompts_list.append(prompt)

    return prompts_list


async def get_prompt_context(
    vstore: VStore, db_release: DocumentRelease, msg: str
) -> tuple[List[str], List[Any]]:
    if not msg:
        return [], []

    base_filter = get_base_filter(db_release)
    original_chunks = await vstore.asimilarity_search(
        msg, k=MAX_CHUNKS, filter=base_filter
    )

    if not original_chunks:
        return [], []

    expanded_chunks = await release_logic_service.get_expanded_chunks(
        vstore, original_chunks
    )

    return build_chunk_prompts(expanded_chunks), expanded_chunks


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


def resolve_citations(
    citations: List[Citation], retrieved_chunks: List[Any]
) -> List[Dict]:
    resolved = []
    # Cria um mapa O(1) de chunk_id para metadados
    chunk_map = {
        chunk.metadata.get('chunk_id'): chunk.metadata
        for chunk in retrieved_chunks
        if chunk.metadata.get('chunk_id')
    }

    seen = set()
    for citation in citations:
        if citation.chunk_id in seen:
            continue

        if citation.chunk_id in chunk_map:
            meta = chunk_map[citation.chunk_id]
            raw_rects = meta.get('rects', [])
            mapped_rects = []
            for r in raw_rects:
                if len(r) == 4:
                    mapped_rects.append({
                        'x1': r[0],
                        'y1': r[1],
                        'x2': r[2],
                        'y2': r[3],
                    })

            resolved.append({
                'chunk_id': citation.chunk_id,
                'text_snippet': citation.text_snippet,
                'page': meta.get('page'),
                'rects': mapped_rects,
            })
            seen.add(citation.chunk_id)

    return resolved


async def create_ai_response(
    session: AsyncSession,
    user_id: UUID,
    doc_id: UUID,
    data: DocumentMessageCreate,
    model: Model,
    vstore: VStore,
    recent_messages: list[DocumentMessage],
) -> Dict:
    releases_list = await release_service.get_releases_by_document(
        session, doc_id
    )
    db_release = await release_service.get_release_with_details(
        session, releases_list[0].id
    )

    auto_prompts = await get_document_auto_context(session, doc_id)
    explicit_prompts = await get_context(session, data.content)

    branch_context, branch_chunks = await get_prompt_context(
        vstore, db_release, '\n---\n'.join(explicit_prompts)
    )

    msg_context, msg_chunks = await get_prompt_context(
        vstore, db_release, data.content
    )

    all_chunks = branch_chunks + msg_chunks
    context = '\n---\n'.join(
        msg_context + branch_context + auto_prompts + explicit_prompts
    )

    chat_context = build_chat_prompt(recent_messages)

    # Opted to omit full document text because now chunks are perfectly mapped to coords
    # full_text is too big and breaks citations if the LLM cites it instead of chunks.
    # full_text = await _load_document_text(db_release)
    # if full_text:
    #     context = f'<CONTEUDO-COMPLETO-DO-DOCUMENTO>\n{full_text}\n</CONTEUDO-COMPLETO-DO-DOCUMENTO>\n\n---\n\n{context}'

    prompt = PROMPTS.CHAT.format(
        context=context,
        content=data.content,
        recent_messages=chat_context,
    )

    structured_model = model.with_structured_output(AnswerWithCitations)
    response: AnswerWithCitations = structured_model.invoke(prompt)

    # Resolve citations
    resolved_citations = resolve_citations(response.citations, all_chunks)

    return {'answer': response.answer, 'references': resolved_citations}
