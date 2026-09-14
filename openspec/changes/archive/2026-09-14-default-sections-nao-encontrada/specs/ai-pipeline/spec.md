## MODIFIED Requirements

### Requirement: Classificação e Vinculação de Macro-seções
O sistema SHALL atribuir a macro-seção padrão "NÃO ENCONTRADA" a todos os blocos de texto gerados no pipeline de ingestão e carimbar o cabeçalho temático correspondente no conteúdo dos blocos de texto, sem realizar chamadas a modelos de linguagem para detecção de seções.

#### Scenario: Identificação de seções e atribuição aos blocos
- **WHEN** blocos de texto são processados na etapa de seções
- **THEN** cada bloco recebe o metadado `section_title` com valor "NÃO ENCONTRADA" e o prefixo `SECTION: NÃO ENCONTRADA\n\n` no conteúdo textual
