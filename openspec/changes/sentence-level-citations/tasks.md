# Tasks

## 1. Segmentação em frases

- [ ] 1.1 Escrever `tests/unit/services/test_sentences.py` com abreviações, listas, linhas de tabela, fragmentos curtos e fragmento final, e verificar que o teste falha antes da mudança.
- [ ] 1.2 Escrever em `tests/unit/services/test_sentences_corpus.py` a verificação de tolerância zero sobre o acervo (todo o texto do chunk em exatamente uma frase, na ordem), e verificar que o teste falha antes da mudança.
- [ ] 1.3 Implementar `lumina/services/ai/stages/sentences.py` e verificar que os testes 1.1 e 1.2 passam.

## 2. Posição das frases na ingestão

- [ ] 2.1 Acrescentar a `tests/unit/services/test_positioning.py` um caso em que `clean_whitespace` altera deslocamentos, exigindo que cada frase receba os retângulos do próprio trecho, e verificar que o teste falha antes da mudança.
- [ ] 2.2 Gravar `sentences` com `start`, `end` e `rects` em `extraction.py` e `positioning.py`, e verificar que o teste 2.1 passa.
- [ ] 2.3 Medir no acervo os fragmentos, as frases sem retângulo e o acréscimo de marcadores. Confirmar o limite de 40 caracteres, investigar as frases sem retângulo e registrar os números em `design.md`.
- [ ] 2.4 Registrar em `test_sentences_corpus.py` os pisos da fração de frases com retângulos e da redução de linhas, com os valores medidos arredondados para baixo, e verificar que o teste passa.

## 3. Anonimização

- [ ] 3.1 Acrescentar a `tests/unit/services/test_metadata_anonymization.py` os casos de frase com `<PERSON_n>`, deslocamento depois de marcador maior ou menor que o nome e entidade na fronteira, e verificar que o teste falha antes da mudança.
- [ ] 3.2 Expor as posições das entidades em `PresidioAnonymizer._anonymize_text`, recalcular `sentences` em `_anonymize_each_chunk` e verificar que o teste 3.1 passa.
- [ ] 3.3 Acrescentar a `tests/unit/services/test_anonymization_corpus.py` a verificação de que nenhum metadado de frase contém nome reconhecido e de que todas as frases cabem no texto anonimizado. É uma guarda: verificar que ela passa.

## 4. Contexto e citações

- [ ] 4.1 Acrescentar a `tests/unit/services/test_citations_contract.py` os cenários de `Citação por Frase`, incluindo número inválido, citação sem frase, frase sem retângulo e chunk antigo, e verificar que os novos casos falham antes da mudança.
- [ ] 4.2 Acrescentar testes de `format_context` e `build_chunk_prompts` para chunks com e sem `sentences`, e verificar que falham antes da mudança.
- [ ] 4.3 Adicionar `sentences` a `Citation`, ajustar `resolve_citations` e o helper de renderização em `retrieval.py`, e verificar que os testes 4.1 e 4.2 passam.
- [ ] 4.4 Atualizar `DOCUMENT_ANALYSIS_PROMPT`, `CHAT` e as descrições dos campos de citação, e verificar com `tests/unit/services/test_evaluation_styles.py` e `test_ai_chat.py` que o estilo e o chat continuam corretos.

## 5. Jornada do analista

- [ ] 5.1 Estender `tests/integration/test_release_pipeline.py` com a jornada do design: o modelo substituído cita uma frase e a resposta traz uma referência menor que o chunk. Verificar que o teste falha antes do grupo 4 e passa depois dele.
- [ ] 5.2 Acrescentar um caso do chat com chunk sem `sentences`, passando por `create_ai_response`. É uma guarda: verificar que ele passa com os retângulos do chunk.
- [ ] 5.3 Atualizar `docs/ia-plataforma.md` com a citação por frase e o fallback para o chunk, e verificar que o texto corresponde ao código.

## 6. Avaliação com modelos reais

- [ ] 6.1 Criar `tests/ai/evaluation/citations/test_citation_precision.py`, com a marca `ai`, reportando se as frases citadas contêm o trecho anotado, a taxa de citações por frase e as linhas destacadas em relação ao chunk.
- [ ] 6.2 Rodar o teste com `--run-ai` e registrar o resultado em `design.md`.

## 7. Verificação final

- [ ] 7.1 Rodar a suíte completa e `ruff`, e registrar aqui o resultado que de fato rodou.

## Workflow follow-up

- Abrir a issue do `lumina-front` para exibir as evidências do chat, com o modelo `.github/ISSUE_TEMPLATE/demanda.md`, e citá-la em `proposal.md`.
- Sincronizar as specs e arquivar a mudança depois da revisão.
