# ai-pipeline Specification

## Purpose
Define a arquitetura modular e os comportamentos esperados para o pipeline de processamento, extração de texto, anonimização LGPD, indexação vetorial e avaliação estruturada de documentos por inteligência artificial.

## Requirements

### Requirement: Extração de Texto e Chunking Geométrico
O sistema SHALL extrair o conteúdo textual de arquivos PDF mantendo o mapeamento de coordenadas físicas (bounding boxes `rects`) de cada linha, gerando blocos de texto (chunks) com tamanho máximo de 500 caracteres e metadados de página e identificador sequencial.

#### Scenario: Extração de documento PDF com coordenadas
- **WHEN** um documento PDF válido é processado pela etapa de extração
- **THEN** o sistema emite blocos com `chunk_id`, número de página `page`, texto sanitizado e caixas delimitadoras `rects` correspondentes às linhas no documento original

#### Scenario: Rejeição de formatos não suportados
- **WHEN** um arquivo com extensão diferente de PDF é fornecido na extração
- **THEN** o sistema SHALL rejeitar o processamento levantando erro de tipo de arquivo não suportado

### Requirement: Classificação e Vinculação de Macro-seções
O sistema SHALL atribuir a macro-seção padrão "NÃO ENCONTRADA" a todos os blocos de texto gerados no pipeline de ingestão e carimbar o cabeçalho temático correspondente no conteúdo dos blocos de texto, sem realizar chamadas a modelos de linguagem para detecção de seções.

#### Scenario: Identificação de seções e atribuição aos blocos
- **WHEN** blocos de texto são processados na etapa de seções
- **THEN** cada bloco recebe o metadado `section_title` com valor "NÃO ENCONTRADA" e o prefixo `SECTION: NÃO ENCONTRADA\n\n` no conteúdo textual

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

### Requirement: Auditoria e Exportação Estruturada de Ingestão de Documentos
O sistema SHALL persistir em disco os artefatos intermediários de processamento e o arquivo PDF anotado com as seções e fragmentos textuais (chunks) delimitados, organizados em diretórios específicos, exclusivamente quando a flag `DEBUG_INGESTION_AUDIT` estiver configurada como verdadeira nas configurações da aplicação.

#### Scenario: Ingestão de documento com auditoria desativada
- **WHEN** um documento PDF é processado pelo motor de ingestão com a flag `DEBUG_INGESTION_AUDIT` desativada (`False`)
- **THEN** o sistema executa todo o processamento, extração, árvore de seções e fatiamento em memória, sem criar diretórios ou persistir arquivos de auditoria no sistema de arquivos local

#### Scenario: Ingestão de documento com auditoria ativada
- **WHEN** um documento PDF é processado pelo motor de ingestão com a flag `DEBUG_INGESTION_AUDIT` ativada (`True`)
- **THEN** o sistema grava os artefatos nos subdiretórios do caminho configurado em `INGESTION_AUDIT_DIRECTORY`:
  - `01_raw_markdown/`: Markdown bruto extraído (`.md`) e mapeamento físico de páginas (`_pages.json`)
  - `02_sections_tree/`: Árvore de seções estruturada em JSON (`_sections.json`) e relatório legível em Markdown (`_sections.md`)
  - `03_chunks/`: Fragmentos textuais finais enriquecidos com retângulos de linha em JSON (`_chunks.json`) e prévia textual em Markdown (`_chunks.md`)
  - `04_annotated_pdfs/`: Arquivo PDF anotado visualmente (`_annotated.pdf`) com barras marginais identificando as seções por papel semântico e caixas destacando os chunks

