## Why

O `PresidioAnonymizer` não mascara nome de pessoa nenhum. O `_setup_analyzer` remove todos os reconhecedores padrão do Presidio, inclusive o único que detecta `PERSON`, e registra só padrões de CPF, CNPJ, telefone, e-mail e afins. O nome de autoria da capa, dos orientadores e dos autores de artigo chega intacto aos embeddings da OpenAI e ao LLM de avaliação, contra o requisito "Anonimização e Proteção de Dados Pessoais" da spec `ai-pipeline`. A issue #22 registrou o sintoma com o nome em maiúsculas do anteprojeto; a investigação mostrou que nomes em caixa mista também passam.

## What Changes

- A anonimização passa a mascarar nomes de pessoa como `<PERSON_n>` em `page_content`, `section_title` e `section_path`.
- A detecção roda em duas passadas por documento:
  - **Coleta:** o modelo spaCy em português procura nomes em todas as seções, menos nas de papel `references`. Trechos em maiúsculas passam para caixa de título antes da análise, porque o modelo não reconhece nomes em caixa alta.
  - **Mascaramento:** cada nome coletado vira um termo do documento, mascarado em qualquer caixa e em qualquer seção, inclusive em References.
- Só entram na coleta nomes com duas ou mais palavras capitalizadas. O filtro descarta candidatos cujas palavras aparecem em minúsculas no próprio documento ("Energias Renováveis") e candidatos iguais a um título de seção.
- Sobrenomes isolados, como os de citações no corpo ("Laubheimer", "FERREIRA et al."), continuam visíveis. Autores que aparecem só em References também.
- As variantes de caixa de um mesmo nome recebem o mesmo marcador, e o mapa de reversão guarda uma forma por marcador.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `ai-pipeline`: o requisito "Anonimização e Proteção de Dados Pessoais" ganha cenários para nomes de pessoa: nome em maiúsculas, nome repetido em outra caixa, nome da autoria em References e autores citados que continuam visíveis.

## Impact

- **Código de produção:** `lumina/utils/PresidioAnonymizer.py` (coleta, filtro e reconhecedor por documento) e `lumina/utils/InstanceCounterAnonymizer.py` (mesmo marcador para variantes de caixa). `lumina/services/ai/stages/anonymization.py` mantém a assinatura.
- **Testes:** `tests/unit/services/test_metadata_anonymization.py` ganha os testes focados. Um teste novo sobre o acervo de `tests/fixtures/documents/` verifica, com tolerância zero, que os nomes de autoria anotados não aparecem nos chunks anonimizados.
- **Acervo:** cada documento ganha a lista dos nomes de autoria que a anonimização precisa mascarar.
- **Recuperação:** os chunks indexados mudam onde havia nomes. `test_retrieval_answer_keys.py` precisa continuar passando, e os pisos de `test_retrieval_baseline.py` são medidos de novo.
- **Desempenho:** a ingestão roda o spaCy uma vez a mais por chunk, na coleta.
- **Documentação:** a seção "Anonimização com Microsoft Presidio" de `docs/ia-plataforma.md`.
- **Débitos:** a ingestão transforma o nome da capa em título de seção (issue a abrir). Esta change mascara o nome nesse título, mas não corrige a árvore de seções.
- Fecha a issue #22.
