## ADDED Requirements

### Requirement: Busca Léxica por Qualquer Termo do Título do Critério
A recuperação de evidências SHALL fundir a busca vetorial com uma busca léxica sobre os chunks do documento avaliado, sem os resumos de seção. A busca léxica SHALL usar o título do ramo como consulta e aceitar chunks que contenham qualquer termo dela. Os chunks com mais ocorrências dos termos em relação ao próprio tamanho SHALL vir antes. Texto do ramo com pontuação ou símbolos SHALL ser tratado como texto, nunca como operador de busca.

#### Scenario: Consulta de várias palavras sem chunk que tenha todas
- **WHEN** a consulta léxica tem várias palavras e nenhum chunk do documento contém todas elas, como "Existência de justificativa da revisão: O manuscrito apresenta uma justificativa clara para a realização da Revisão Sistemática?"
- **THEN** a busca léxica devolve os chunks que contêm algum termo da consulta, com o chunk que trata da justificativa da revisão em primeiro lugar

#### Scenario: Ramos com evidência no acervo anotado em português
- **WHEN** a recuperação busca, num documento em português do acervo anotado, um ramo do gabarito com evidência esperada
- **THEN** a busca léxica com o título do ramo devolve ao menos um chunk desse documento

#### Scenario: Chunk longo com termos repetidos
- **WHEN** um chunk curto e um chunk longo contêm os termos da consulta e o chunk longo repete esses termos em meio a muito texto sem relação
- **THEN** a busca léxica põe o chunk curto antes do longo

#### Scenario: Descrição do ramo fora da consulta léxica
- **WHEN** a recuperação busca um ramo com título e descrição
- **THEN** a busca léxica recebe só o título, e a busca vetorial recebe o título e a descrição

#### Scenario: Chunks de outro documento e resumos de seção
- **WHEN** outro documento indexado e os resumos de seção do documento avaliado contêm termos do ramo
- **THEN** a busca léxica não devolve esses chunks

#### Scenario: Ramo com caracteres de sintaxe de busca
- **WHEN** a consulta léxica contém símbolos como `&`, `|`, `!`, `:`, `(` ou aspas
- **THEN** a busca léxica trata os símbolos como texto e devolve chunks sem erro

#### Scenario: Ramo sem termo pesquisável
- **WHEN** o título do ramo está vazio ou só tem palavras sem valor de busca, como artigos e preposições
- **THEN** a busca léxica devolve uma lista vazia sem erro e a fusão usa só a busca vetorial
