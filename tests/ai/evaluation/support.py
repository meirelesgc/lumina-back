"""
Apoio comum aos testes de avaliação com IA sobre o acervo anotado: base
vetorial ligada ao container de teste, ingestão dos PDFs anotados pelo
caminho de produção, entrada de cada ramo do gabarito na forma que a
recuperação recebe e seleção de seções de cada ramo.
"""

import asyncio
from pathlib import Path
from types import SimpleNamespace

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from lumina.core.settings import Settings
from lumina.services.ai.pipeline import run_document_ingestion
from lumina.services.ai.stages import retrieval
from lumina.services.ai.stages.outline import (
    OutlineSection,
    build_outline,
    outline_markdown,
)
from lumina.services.ai.stages.selection import select_payload
from tests.fixtures.answer_keys import (
    RETRIEVAL_KEYS,
    anonymized,
    expected_branches,
    pdf_for,
)


def build_vectorstore(connection) -> PGVector:
    # Mesmos parâmetros de lumina/core/vectorstore.py, ligados ao container.
    return PGVector(
        embeddings=OpenAIEmbeddings(
            model='text-embedding-3-small',
            api_key=Settings().OPENAI_API_KEY,
        ),
        connection=connection,
        use_jsonb=True,
        async_mode=True,
    )


async def ingest_answer_keys(vstore: PGVector) -> None:
    """Ingere todos os PDFs anotados na mesma coleção, como em produção."""
    for key in RETRIEVAL_KEYS:
        await run_document_ingestion(pdf_for(key), vstore, model=None)


def document_filter(retrieval_key: Path) -> dict:
    """Filtro de produção que isola os chunks do PDF do gabarito."""
    return retrieval.get_base_filter(
        SimpleNamespace(file_path=str(pdf_for(retrieval_key)))
    )


def branch_query(taxonomy: dict, branch: dict) -> tuple[dict, dict]:
    """Taxonomia e ramo do gabarito na forma que a recuperação recebe."""
    return (
        {'title': taxonomy['title']},
        {
            'id': branch['id'],
            'title': branch['title'],
            'description': branch['description'],
        },
    )


async def select_answer_key(
    retrieval_key: Path,
    model: BaseChatModel,
    semaphore: asyncio.Semaphore,
) -> tuple[list[OutlineSection], list[tuple[dict, dict]]]:
    """
    Sumário do PDF do gabarito e o payload de seleção de cada ramo, com o
    escopo e a dica de seção anotados. Os chunks são os mesmos que a
    ingestão gera: extraídos e anonimizados.
    """
    chunks = await asyncio.to_thread(anonymized, pdf_for(retrieval_key))
    outline = build_outline(chunks)
    outline_md = outline_markdown(outline)

    async def run(taxonomy: dict, branch: dict) -> tuple[dict, dict]:
        async with semaphore:
            payload = await select_payload(
                model,
                outline,
                *branch_query(taxonomy, branch),
                branch.get('section_requirement'),
                outline_md,
            )
        return branch, payload

    pairs = await asyncio.gather(*[
        run(taxonomy, branch)
        for taxonomy, branch in expected_branches(retrieval_key)
    ])
    return outline, list(pairs)


def usage_report(usage: dict[str, dict], label: str = 'Consumo') -> list[str]:
    """
    Consumo por modelo coletado por `get_usage_metadata_callback`: tokens de
    entrada (e quantos vieram do cache), de saída e de raciocínio, que a
    OpenAI cobra como saída.
    """
    lines = [label]
    for model, data in sorted(usage.items()):
        cached = (data.get('input_token_details') or {}).get('cache_read', 0)
        reasoning = (data.get('output_token_details') or {}).get(
            'reasoning', 0
        )
        lines.append(
            f'  {model}: entrada {data["input_tokens"]} '
            f'(cache {cached}) | saída {data["output_tokens"]} '
            f'(raciocínio {reasoning})'
        )
    return lines
