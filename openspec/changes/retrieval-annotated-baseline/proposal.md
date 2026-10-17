## Why

O acervo anotado de `tests/fixtures/documents/` mede a ingestão até os chunks, mas nada mede o que a recuperação de evidências entrega ao avaliador. O parecer de cada critério da árvore depende dos trechos que `/release` recupera para ele. Hoje ninguém sabe quantos desses trechos são os certos, nem se a recuperação confunde critérios vizinhos da mesma seção. Antes de mexer no roteamento por seção, na busca híbrida ou na expansão de vizinhos, o time precisa de um placar do estado atual para medir cada mudança contra ele.

## What Changes

- Novo gabarito `<nome>.retrieval.yaml`, ao lado do PDF e do `<nome>.sections.yaml`. No mesmo arquivo ficam a árvore de critérios (tipificação, taxonomia e ramo) e, para cada ramo, os trechos que a recuperação precisa devolver, com seção, página e um trecho copiado do PDF. Expansões de consulta e requisito de seção entram como campos opcionais do ramo. O modelo fica em `tests/fixtures/documents/retrieval_template.yaml`.
- O usuário anota os gabaritos. A implementação começa depois disso.
- Novo teste de consistência dos gabaritos, sem IA, na suíte padrão. Tolerância zero: cada trecho anotado existe no texto anonimizado dos chunks da seção e da página indicadas, e cada seção existe no `<nome>.sections.yaml`.
- Novo teste de avaliação da recuperação, com `@pytest.mark.ai` (embeddings reais da OpenAI e pgvector):
  - **Crítico, tolerância zero:** nenhuma evidência recuperada vem de outro documento.
  - **Métricas com piso, somadas sobre o acervo:** recall de trechos, acerto de seção e página, precisão entre ramos e acerto do roteamento por seção. O teste imprime o placar por documento e por ramo. Cada piso nasce com o valor medido na implementação, arredondado para baixo, e só sobe.
- O container PostgreSQL dos testes passa de `postgres:16` para `pgvector/pgvector:pg16`.
- A normalização dos testes trata como iguais as aspas retas e curvas e o hífen e os travessões, para o anotador não depender da tipografia do PDF.
- O acervo de recuperação cobre três documentos: o anteprojeto, com a árvore de Validação de Ante-Projeto, e as duas revisões sistemáticas, com a árvore de Revisão Sistemática da Literatura.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `ai-pipeline`: adiciona o critério de aceite da recuperação de evidências sobre o acervo anotado.

## Impact

- **Código de produção:** nenhum. A mudança registra o comportamento atual de `retrieve_criteria_payload` e `route_candidate_sections` em `lumina/services/ai/stages/retrieval.py`.
- **Testes:** novo `tests/unit/services/test_retrieval_answer_keys.py`, novo `tests/ai/evaluation/retrieval/test_retrieval_baseline.py`, leitura dos gabaritos extraída de `tests/unit/services/test_ingestion_sections.py` para `tests/fixtures/answer_keys.py`, imagem do container em `tests/conftest.py`.
- **Acervo:** `retrieval_template.yaml` e uma seção nova em `tests/fixtures/documents/README.md`. Os `*.retrieval.yaml` de cada documento vêm do usuário.
- **Custo:** o teste de avaliação gera embeddings de todos os chunks do acervo anotado a cada execução de `poetry run task test-ai`.
- **Documentação:** seção sobre a validação da recuperação em `docs/arquitetura-engenharia.md`.
- **Débitos registrados:** #22 (nome em maiúsculas sem anonimização), #23 (placar com entradas geradas por LLM), #24 (limite do roteamento por seção) e #25 (palavras hifenizadas em tabelas).
