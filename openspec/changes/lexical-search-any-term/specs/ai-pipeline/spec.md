## ADDED Requirements

### Requirement: Busca Léxica por Qualquer Termo do Título do Critério
A recuperação SHALL fundir a busca vetorial com uma busca léxica sobre os chunks do documento avaliado, sem os resumos de seção. A busca léxica SHALL consultar o título do ramo e, sem resultado, o título e a descrição. Ela SHALL aceitar chunks com qualquer termo da consulta e pôr antes os que têm mais ocorrências dos termos em relação ao próprio tamanho.

#### Scenario: Consulta de várias palavras sem chunk que tenha todas
- **WHEN** a consulta léxica tem várias palavras e nenhum chunk do documento contém todas elas, como "Existência de justificativa da revisão: O manuscrito apresenta uma justificativa clara para a realização da Revisão Sistemática?"
- **THEN** a busca léxica devolve os chunks que contêm algum termo da consulta, com o chunk que trata da justificativa da revisão em primeiro lugar

#### Scenario: Ramos com evidência no acervo anotado em português
- **WHEN** a recuperação busca, num documento em português do acervo anotado, um ramo do gabarito com evidência esperada
- **THEN** a busca léxica do ramo devolve ao menos um chunk desse documento

#### Scenario: Título sem termo no documento
- **WHEN** nenhum termo do título do ramo aparece no documento, como o ramo de título "Título" num anteprojeto que não usa essa palavra
- **THEN** a busca léxica repete a consulta com o título e a descrição do ramo

#### Scenario: Chunk longo com termos repetidos
- **WHEN** um chunk curto e um chunk longo contêm os termos da consulta e o chunk longo repete esses termos em meio a muito texto sem relação
- **THEN** a busca léxica põe o chunk curto antes do longo

#### Scenario: Descrição do ramo fora da consulta léxica
- **WHEN** a recuperação busca um ramo com título e descrição
- **THEN** a busca léxica recebe só o título quando ele encontra chunks, e a busca vetorial recebe o título e a descrição

#### Scenario: Chunks de outro documento e resumos de seção
- **WHEN** outro documento indexado e os resumos de seção do documento avaliado contêm termos do ramo
- **THEN** a busca léxica não devolve esses chunks

#### Scenario: Ramo com caracteres de sintaxe de busca
- **WHEN** a consulta léxica contém símbolos como `&`, `|`, `!`, `:`, `(` ou aspas
- **THEN** a busca léxica trata os símbolos como texto e devolve chunks sem erro

#### Scenario: Ramo sem termo pesquisável
- **WHEN** o título e a descrição do ramo estão vazios ou só têm palavras sem valor de busca, como artigos e preposições
- **THEN** a busca léxica devolve uma lista vazia sem erro e a fusão usa só a busca vetorial
