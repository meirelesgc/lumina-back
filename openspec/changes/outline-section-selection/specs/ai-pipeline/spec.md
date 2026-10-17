## ADDED Requirements

### Requirement: Seleção de Seções pelo Sumário do Documento
O sistema SHALL escolher o contexto de cada critério a partir do sumário do documento, que lista cada seção com identificador, caminho de títulos, páginas, tamanho estimado e o início do texto. Para critérios de escopo de seção ou indeterminado, um seletor SHALL pedir seções pelo identificador, ler o texto integral delas e decidir se o conteúdo basta, pedir outras seções ou concluir que o conteúdo não existe no documento, em no máximo 3 rodadas. Critérios de escopo de documento inteiro SHALL receber todas as seções sem passar pelo seletor. Cada veredito SHALL registrar a seleção que o gerou.

#### Scenario: Critério de seção com conteúdo encontrado
- **WHEN** um critério de escopo de seção é avaliado e o seletor indica que as seções lidas bastam
- **THEN** o avaliador recebe o texto integral dessas seções com os identificadores de chunk, e o veredito registra as seções, o motivo, as rodadas e os tokens

#### Scenario: Critério de documento inteiro
- **WHEN** um critério de escopo de documento inteiro é avaliado
- **THEN** o avaliador recebe todas as seções do documento e o seletor não é chamado

#### Scenario: Limite de rodadas
- **WHEN** o seletor ainda pede seções ao fim da terceira rodada
- **THEN** a seleção termina e o avaliador recebe todas as seções lidas até ali

#### Scenario: Conteúdo inexistente
- **WHEN** o seletor conclui, depois de ler ao menos uma seção, que o conteúdo do critério não existe no documento
- **THEN** o critério recebe "não contempla", nota 0 e um parecer padrão que lista as seções inspecionadas, sem chamar o avaliador

#### Scenario: Identificador de seção inexistente
- **WHEN** o seletor pede um identificador que não está no sumário
- **THEN** o identificador é ignorado e registrado na seleção

#### Scenario: Saída inválida do seletor
- **WHEN** o seletor devolve uma saída fora do formato esperado depois das retentativas
- **THEN** o critério recebe o documento inteiro, e a seleção registra a falha

### Requirement: Critério de Aceite da Seleção de Seções sobre Acervo Anotado
A seleção de seções SHALL ser validada contra o acervo anotado de recuperação. O recall de trechos SHALL contar os trechos anotados presentes no contexto enviado ao avaliador. O acerto de veredicto SHALL comparar o `fulfilled` da avaliação com o anotado, e ramos sem evidência anotada SHALL contar como não contemplados. As métricas SHALL somar o acervo inteiro e falhar abaixo de um piso registrado, que só sobe.

#### Scenario: Recall da seleção abaixo do piso
- **WHEN** a fração de trechos anotados presentes no contexto selecionado, somada sobre o acervo, fica abaixo do piso registrado
- **THEN** a validação falha e informa o placar por documento e por critério, com as seções escolhidas e as rodadas

#### Scenario: Acerto de veredicto abaixo do piso
- **WHEN** a fração de critérios cujo `fulfilled` coincide com o anotado fica abaixo do piso registrado
- **THEN** a validação falha e informa os acertos e erros por documento e por critério

#### Scenario: Conclusão de inexistência errada
- **WHEN** o seletor conclui que o conteúdo não existe para um critério que tem evidência anotada
- **THEN** o placar conta o caso como erro de inexistência e o lista no relatório

## MODIFIED Requirements

### Requirement: Avaliação Estruturada de Critérios com Resolução de Citações
O sistema SHALL avaliar concorrentemente critérios normativos utilizando as seções do documento escolhidas pela seleção de seções, com o texto integral de cada seção e os identificadores de chunk, retornando parecer técnico, nota no barema de 0 a 10, flag de atendimento e coordenadas visuais das evidências citadas. O parecer SHALL ser curto, em Markdown estruturado (listas ou tabela, sem parágrafos longos), seguindo um estilo de resposta sorteado de forma independente para cada critério, e SHALL conter sugestões de melhoria apenas para lacunas identificadas, limitadas a uma ação por lacuna.

#### Scenario: Avaliação de critério normativo com evidência no documento
- **WHEN** um critério normativo é avaliado contra as seções selecionadas
- **THEN** a resposta contém nota de 0 a 10, parecer fundamentado, e os `chunk_id` citados são resolvidos em retângulos físicos `rects` para destaque visual no visualizador de PDF

#### Scenario: Detecção de alucinação de citações
- **WHEN** o modelo de linguagem cita um identificador de bloco inexistente nos trechos fornecidos
- **THEN** o sistema sinaliza a citação como alucinação e registra a métrica na telemetria de auditoria

#### Scenario: Estilo de resposta sorteado por critério
- **WHEN** os critérios de uma release são enviados para avaliação
- **THEN** cada critério recebe, de forma independente, um estilo de resposta sorteado entre os estilos de parecer disponíveis (Veredito + listas, Checklist, Tabela, Resumo + tópicos), mantendo inalterados o barema, as regras de citação e o formato JSON de saída

#### Scenario: Estilo mantido nas retentativas
- **WHEN** a avaliação em lote de uma release é repetida por falha transitória
- **THEN** cada critério é reavaliado com o mesmo estilo sorteado na primeira tentativa

#### Scenario: Critério integralmente atendido
- **WHEN** o modelo conclui que o critério é atendido integralmente
- **THEN** o parecer apresenta apenas a situação e as evidências, sem sugestões de melhoria

#### Scenario: Critério parcialmente atendido ou não atendido
- **WHEN** o modelo identifica lacunas no atendimento do critério
- **THEN** o parecer lista as lacunas e propõe no máximo uma ação curta por lacuna

#### Scenario: Todo critério recebe veredito
- **WHEN** uma release é avaliada
- **THEN** cada critério da árvore recebe um veredito, inclusive os que o seletor conclui não existirem no documento

### Requirement: Auditoria e Exportação Estruturada de Ingestão de Documentos
O sistema SHALL persistir em disco os artefatos intermediários de processamento, o arquivo PDF anotado com as seções e fragmentos textuais (chunks) delimitados, o sumário do documento e a seleção de seções de cada critério, organizados em diretórios específicos, exclusivamente quando a flag `DEBUG_INGESTION_AUDIT` estiver configurada como verdadeira nas configurações da aplicação.

#### Scenario: Ingestão de documento com auditoria desativada
- **WHEN** um documento PDF é processado pelo motor de ingestão com a flag `DEBUG_INGESTION_AUDIT` desativada (`False`)
- **THEN** o sistema executa todo o processamento, extração, árvore de seções, fatiamento e seleção de seções em memória, sem criar diretórios ou persistir arquivos de auditoria no sistema de arquivos local

#### Scenario: Ingestão de documento com auditoria ativada
- **WHEN** um documento PDF é processado pelo motor de ingestão com a flag `DEBUG_INGESTION_AUDIT` ativada (`True`)
- **THEN** o sistema grava os artefatos nos subdiretórios do caminho configurado em `INGESTION_AUDIT_DIRECTORY`:
  - `01_raw_markdown/`: Markdown bruto extraído (`.md`) e mapeamento físico de páginas (`_pages.json`)
  - `02_sections_tree/`: Árvore de seções estruturada em JSON (`_sections.json`) e relatório legível em Markdown (`_sections.md`)
  - `03_chunks/`: Fragmentos textuais finais enriquecidos com retângulos de linha em JSON (`_chunks.json`) e prévia textual em Markdown (`_chunks.md`)
  - `04_annotated_pdfs/`: Arquivo PDF anotado visualmente (`_annotated.pdf`) com barras marginais identificando as seções por papel semântico e caixas destacando os chunks

#### Scenario: Seleção de seções com auditoria ativada
- **WHEN** os critérios de uma release são avaliados com a flag `DEBUG_INGESTION_AUDIT` ativada (`True`)
- **THEN** o sistema grava o sumário do documento, exatamente como o seletor o recebe, em `05_outline/<documento>.md`, e, para cada critério, as rodadas do seletor, o contexto enviado ao avaliador e o veredito em `06_selection/<documento>/<critério>.md`

## REMOVED Requirements

### Requirement: Fusão de Consultas Expandidas por Reciprocal Rank Fusion
**Reason**: A avaliação deixa de usar a busca vetorial. O contexto de cada critério vem da seleção de seções pelo sumário, e as expansões de consulta não entram mais no contexto enviado ao avaliador.
**Migration**: Os vereditos já gravados mantêm a versão de expansão registrada. O serviço de expansão continua gerando expansões até que a issue #28 decida se elas viram dica do seletor ou se o serviço sai.
