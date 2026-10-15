## ADDED Requirements

### Requirement: Consulta de Recuperação por Critério
O sistema SHALL montar a consulta de recuperação de cada critério (`branch`) com o título e a descrição do critério, no formato `<título>: <descrição>`, ou só com o que existir quando um dos dois estiver vazio. A consulta SHALL NOT conter o título da taxonomia nem um cabeçalho de seção. O sistema SHALL usar esse mesmo texto na busca vetorial e na busca léxica, e SHALL consultar cada expansão ativa pelo próprio texto, sem prefixo.

#### Scenario: Critério com título e descrição
- **WHEN** o sistema recupera evidências para o critério "Existência de justificativa da revisão", de descrição "O manuscrito apresenta uma justificativa clara?", sob a taxonomia "Fundamentação da Revisão"
- **THEN** a busca vetorial e a busca léxica recebem "Existência de justificativa da revisão: O manuscrito apresenta uma justificativa clara?"
- **AND** nenhuma consulta contém "Fundamentação da Revisão"

#### Scenario: Critério sem descrição
- **WHEN** o critério tem título e a descrição está vazia
- **THEN** a consulta é o título do critério

#### Scenario: Critério com expansões ativas
- **WHEN** o critério tem expansões de consulta ativas
- **THEN** o sistema faz uma busca vetorial com a consulta do critério e uma com o texto de cada expansão, sem acrescentar título de taxonomia ou de seção

#### Scenario: Auditoria registra a consulta usada
- **WHEN** a recuperação de um critério termina
- **THEN** o campo `retriever_query` do resultado guarda a consulta do critério usada na busca

### Requirement: Efeito do Escopo de Busca do Critério
O sistema SHALL usar o escopo de busca ativo do critério para decidir onde procurar as evidências. Com escopo `SPECIFIC_SECTION`, o sistema SHALL restringir a busca às seções do documento cujo resumo fica dentro do limiar de distância da seção esperada, e SHALL buscar no documento inteiro quando nenhuma seção atingir o limiar. Com escopo `ENTIRE_DOCUMENT`, `UNKNOWN` ou sem análise ativa, o sistema SHALL buscar no documento inteiro, sem roteamento por seção.

#### Scenario: Seção específica encontrada
- **WHEN** o critério tem escopo `SPECIFIC_SECTION` e a seção esperada corresponde ao resumo de uma seção do documento dentro do limiar
- **THEN** a busca vetorial considera só os chunks dessa seção

#### Scenario: Seção específica ausente no documento
- **WHEN** o critério tem escopo `SPECIFIC_SECTION` e nenhum resumo de seção fica dentro do limiar
- **THEN** a busca vetorial considera todos os chunks do documento

#### Scenario: Critério transversal ao documento
- **WHEN** o critério tem escopo `ENTIRE_DOCUMENT`
- **THEN** o sistema não consulta os resumos de seção
- **AND** a busca vetorial considera todos os chunks do documento

#### Scenario: Critério sem escopo definido
- **WHEN** o critério tem escopo `UNKNOWN` ou não tem análise de escopo ativa
- **THEN** o sistema não consulta os resumos de seção
- **AND** a busca vetorial considera todos os chunks do documento

### Requirement: Contexto Acadêmico na Análise de Escopo e na Expansão de Consultas
O sistema SHALL pedir a análise de escopo e a expansão de consultas de cada critério com a tipificação, a taxonomia e o critério, e SHALL descrever ao modelo os documentos que o Lumina avalia: artigos, revisões sistemáticas, anteprojetos e relatórios técnicos. Os exemplos de seção específica SHALL ser seções desses documentos, e o pedido SHALL NOT usar exemplos de editais ou instrumentos convocatórios. A expansão de consultas SHALL pedir formulações escritas como o trecho do documento que atenderia ao critério, em forma afirmativa.

#### Scenario: Análise de escopo de critério de revisão sistemática
- **WHEN** o sistema analisa o escopo do critério "Existência de justificativa da revisão" da tipificação "Revisão Sistemática"
- **THEN** o pedido enviado ao modelo traz a tipificação, a taxonomia e o critério
- **AND** traz exemplos de seções de documentos acadêmicos, como Introdução e Metodologia
- **AND** não traz exemplos de editais, como "Habilitação Jurídica" ou "Termo de Referência"

#### Scenario: Expansão de consultas em forma de trecho
- **WHEN** o sistema gera as expansões de consulta de um critério
- **THEN** o pedido enviado ao modelo descreve os documentos acadêmicos e técnicos avaliados
- **AND** pede formulações afirmativas, no estilo do texto do documento, sem palavras de enunciado como "o manuscrito apresenta"
