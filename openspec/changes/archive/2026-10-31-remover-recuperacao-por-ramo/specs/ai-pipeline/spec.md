# Spec Delta

## ADDED Requirements

### Requirement: Árvore de Seções e Metadados dos Chunks
O sistema SHALL montar a árvore de seções do documento a partir dos títulos do Markdown extraído, sem chamadas a modelos de linguagem, e SHALL classificar o papel semântico de cada seção (resumo, introdução, metodologia etc.) por aliases de título e por posição. Cada chunk SHALL carregar o título da seção que o contém em `section_title`, o caminho de títulos em `section_path`, o papel em `section_role` e o prefixo `[título da seção] ` no conteúdo.

#### Scenario: Atribuição de seção aos chunks
- **WHEN** o sistema gera os chunks de uma seção da árvore
- **THEN** cada chunk recebe `section_title`, `section_path` e `section_role` da seção e começa com `[título da seção] `

#### Scenario: Classificação de papel por alias
- **WHEN** o título de uma seção corresponde a um alias conhecido, como "Resumo" ou "Abstract"
- **THEN** a seção recebe o papel correspondente e `role_confidence` igual a `alias_match`

### Requirement: Indexação Apenas de Chunks
A ingestão SHALL indexar na base vetorial apenas os chunks do documento.

#### Scenario: Indexação só de chunks
- **WHEN** o sistema indexa um documento
- **THEN** a base vetorial recebe os chunks do documento e nenhum resumo de seção

### Requirement: Validação dos Gabaritos do Acervo Anotado
Cada PDF anotado SHALL ter um gabarito que reúne a árvore de critérios a avaliar e, para cada critério, os trechos esperados, com página, um trecho do texto do documento e, quando o trecho pertence a uma seção anotada, a seção. A suíte padrão SHALL validar o gabarito sem chamar modelos.

#### Scenario: Trecho anotado inexistente no documento indexado
- **WHEN** um trecho do gabarito não aparece no texto anonimizado dos chunks da página anotada e, quando o gabarito informa a seção, dessa seção
- **THEN** a validação do gabarito falha sem chamar modelos e aponta o documento, o critério e o trecho

#### Scenario: Seção anotada fora do gabarito de seções
- **WHEN** um trecho do gabarito cita uma seção que não está no gabarito de seções do mesmo documento
- **THEN** a validação do gabarito falha e aponta o documento, o critério e a seção

#### Scenario: Trecho fora das seções anotadas
- **WHEN** um trecho do gabarito não informa seção, como o título na capa
- **THEN** a validação do gabarito confere só a página

### Requirement: Recuperação Híbrida do Chat
O chat SHALL fundir a busca vetorial com uma busca léxica sobre os chunks do documento da conversa. A busca léxica SHALL aceitar chunks com qualquer termo da mensagem e pôr antes os que têm mais ocorrências dos termos em relação ao próprio tamanho.

#### Scenario: Mensagem de várias palavras sem chunk que tenha todas
- **WHEN** a mensagem tem várias palavras e nenhum chunk do documento contém todas elas
- **THEN** a busca léxica devolve os chunks que contêm algum termo da mensagem

#### Scenario: Chunk longo com termos repetidos
- **WHEN** um chunk curto e um chunk longo contêm os termos da mensagem e o chunk longo repete esses termos em meio a muito texto sem relação
- **THEN** a busca léxica põe o chunk curto antes do longo

#### Scenario: Chunks de outro documento
- **WHEN** outro documento indexado contém os termos da mensagem
- **THEN** a busca léxica não devolve esses chunks

#### Scenario: Mensagem com caracteres de sintaxe de busca
- **WHEN** a mensagem contém símbolos como `&`, `|`, `!`, `:`, `(` ou aspas
- **THEN** a busca léxica trata os símbolos como texto e devolve chunks sem erro

#### Scenario: Mensagem sem termo pesquisável
- **WHEN** a mensagem está vazia ou só tem palavras sem valor de busca, como artigos e preposições
- **THEN** a busca léxica devolve uma lista vazia sem erro e a fusão usa só a busca vetorial

## REMOVED Requirements

### Requirement: Árvore de Seções e Vinculação aos Chunks
**Reason**: A ingestão deixou de indexar resumos de seção, e a remoção de um cenário exige substituir o requisito.
**Migration**: O requisito "Árvore de Seções e Metadados dos Chunks" mantém os demais comportamentos.

### Requirement: Critério de Aceite da Recuperação sobre Acervo Anotado
**Reason**: A avaliação usa a seleção de seções, e o caminho que este placar media não tem uso em produção.
**Migration**: O requisito "Critério de Aceite da Seleção de Seções sobre Acervo Anotado" mede o contexto que chega ao avaliador. A validação dos gabaritos passa para o requisito "Validação dos Gabaritos do Acervo Anotado".

### Requirement: Busca Léxica por Qualquer Termo do Título do Critério
**Reason**: A busca por ramo saiu com a recuperação por ramo. Só o chat usa a busca léxica.
**Migration**: O requisito "Recuperação Híbrida do Chat" descreve o comportamento que continua em produção.
