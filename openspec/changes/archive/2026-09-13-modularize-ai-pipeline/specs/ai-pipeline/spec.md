## Purpose

Define a arquitetura modular e os comportamentos esperados para o pipeline de processamento, extração de texto, anonimização LGPD, indexação vetorial e avaliação estruturada de documentos por inteligência artificial.

## ADDED Requirements

### Requirement: Extração de Texto e Chunking Geométrico
O sistema SHALL extrair o conteúdo textual de arquivos PDF mantendo o mapeamento de coordenadas físicas (bounding boxes `rects`) de cada linha, gerando blocos de texto (chunks) com tamanho máximo de 500 caracteres e metadados de página e identificador sequencial.

#### Scenario: Extração de documento PDF com coordenadas
- **WHEN** um documento PDF válido é processado pela etapa de extração
- **THEN** o sistema emite blocos com `chunk_id`, número de página `page`, texto sanitizado e caixas delimitadoras `rects` correspondentes às linhas no documento original

#### Scenario: Fallback para arquivos sem layout fixo
- **WHEN** um documento TXT ou DOCX é processado pela etapa de extração
- **THEN** o sistema emite blocos com texto sanitizado, `page` igual a 0 e lista de `rects` vazia

### Requirement: Classificação e Vinculação de Macro-seções
O sistema SHALL identificar os limites de macro-seções normativas no texto do documento e carimbar o cabeçalho temático correspondente no conteúdo dos blocos de texto.

#### Scenario: Identificação de seções e atribuição aos blocos
- **WHEN** blocos de texto são analisados para identificação de seções
- **THEN** cada bloco tem seu ponto médio associado à seção correspondente e recebe o prefixo `SECTION: <Nome da Seção>`

### Requirement: Anonimização e Proteção de Dados Pessoais
O sistema SHALL mascarar informações de dados pessoais sensíveis (PII) nos blocos de texto antes de qualquer operação de vetorização ou envio para provedores de LLM externos, mantendo os dados de reversão isolados exclusivamente nos metadados.

#### Scenario: Anonimização de documentos contendo PII
- **WHEN** blocos contendo CPFs, CNPJs ou nomes são processados
- **THEN** as ocorrências são substituídas por marcadores indexados e o mapa de reversão é armazenado apenas no metadado `presidio_mapping`

### Requirement: Avaliação Estruturada de Critérios com Resolução de Citações
O sistema SHALL avaliar concorrentemente critérios normativos utilizando trechos recuperados do documento com expansão de margem ($\pm 2$), retornando parecer técnico, nota no barema de 0 a 10, flag de atendimento e coordenadas visuais das evidências citadas.

#### Scenario: Avaliação de critério normativo com evidência no documento
- **WHEN** um critério normativo é avaliado contra trechos recuperados
- **THEN** a resposta contém nota de 0 a 10, parecer fundamentado, e os `chunk_id` citados são resolvidos em retângulos físicos `rects` para destaque visual no visualizador de PDF

#### Scenario: Detecção de alucinação de citações
- **WHEN** o modelo de linguagem cita um identificador de bloco inexistente nos trechos fornecidos
- **THEN** o sistema sinaliza a citação como alucinação e registra a métrica na telemetria de auditoria

### Requirement: Síntese Executiva Consolidada
O sistema SHALL sintetizar os resultados gerais da avaliação com base nos critérios de maior e menor pontuação, particionando o texto em seções de saudação, pontos atendidos, pontos a aprimorar e orientação final.

#### Scenario: Geração da síntese executiva
- **WHEN** a avaliação de todos os critérios da árvore é finalizada
- **THEN** o sistema gera a síntese executiva estruturada e a salva no resumo da release
