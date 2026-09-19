## Why

O mecanismo atual de identificação de seções por LLM (em janelas de 3.000 caracteres) consome chamadas de IA desnecessárias na ingestão e será substituído futuramente por uma nova estratégia. Para isolar o pipeline e permitir o desacoplamento antes da introdução do novo método, é necessário remover a lógica atual de detecção e estabelecer um valor padrão estável ("NÃO ENCONTRADA") para a seção de todos os blocos de texto, mantendo a integridade dos metadados e do fluxo downstream do RAG.

## What Changes

- **Remoção da extração por LLM**: Remove o particionamento em janelas de 3.000 caracteres, a invocação do modelo com structured output (`ChunkSections`) e a reconciliação de âncoras (`normalize_with_mapping`, `find_valid_sections`).
- **Atribuição padrão "NÃO ENCONTRADA"**:
  - Para arquivos PDF: todos os chunks recebem `section_title = "NÃO ENCONTRADA"` em seus metadados e o prefixo `SECTION: NÃO ENCONTRADA\n\n` em `page_content`.
  - Para arquivos DOCX/TXT: o documento bruto é atribuído integralmente à seção `"NÃO ENCONTRADA"`, preservando o fatiamento e a formatação downstream.
- **Simplificação do estágio de telemetria**: A etapa `sections` continua registrando a execução no `RunLogger`, retornando telemetria limpa com 0 seções complexas detectadas e taxa de sucesso 1.0.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capacidade necessária neste momento -->

### Modified Capabilities
- `ai-pipeline`: Modifica o comportamento do requisito de *Classificação e Vinculação de Macro-seções* para atribuir de forma padrão e determinística a seção `"NÃO ENCONTRADA"` a todos os blocos gerados na ingestão.

## Impact

- **Código Afetado**:
  - `lumina/services/ai/stages/sections.py`: substituição das funções de identificação e mapeamento complexo por fallback direto.
  - `lumina/services/ai/pipeline.py`: continua chamando `assign_sections_with_telemetry` e `split_sections_with_telemetry` sem quebra de contrato.
- **APIs e Dependências**: Sem alterações na interface pública de rotas ou banco de dados. Elimina chamadas a provedores de LLM durante o estágio `sections`.
- **RAG e Vetorização**: Chunks persistidos no PGVector conterão `section_title: "NÃO ENCONTRADA"` e o prefixo `SECTION: NÃO ENCONTRADA\n\n`.
