## ADDED Requirements

### Requirement: Busca Léxica por Qualquer Termo do Critério
A recuperação de evidências SHALL fundir a busca vetorial com uma busca léxica sobre os chunks do documento avaliado, sem os resumos de seção. A busca léxica SHALL usar o título e a descrição do ramo como consulta e aceitar chunks que contenham qualquer termo dela. Os chunks com mais termos e mais ocorrências do ramo SHALL vir antes. Texto do ramo com pontuação ou símbolos SHALL ser tratado como texto, nunca como operador de busca.

#### Scenario: Ramo de várias palavras sem chunk que tenha todas
- **WHEN** o ramo tem título e descrição com várias palavras e nenhum chunk do documento contém todas elas, como "Existência de justificativa da revisão: O manuscrito apresenta uma justificativa clara para a realização da Revisão Sistemática?"
- **THEN** a busca léxica devolve os chunks que contêm algum termo do ramo, com o chunk que trata da justificativa da revisão em primeiro lugar

#### Scenario: Ramos com evidência no acervo anotado em português
- **WHEN** a recuperação busca, num documento em português do acervo anotado, um ramo do gabarito com evidência esperada
- **THEN** a busca léxica devolve ao menos um chunk desse documento

#### Scenario: Chunks de outro documento e resumos de seção
- **WHEN** outro documento indexado e os resumos de seção do documento avaliado contêm termos do ramo
- **THEN** a busca léxica não devolve esses chunks

#### Scenario: Ramo com caracteres de sintaxe de busca
- **WHEN** o título ou a descrição do ramo contém símbolos como `&`, `|`, `!`, `:`, `(` ou aspas
- **THEN** a busca léxica trata os símbolos como texto e devolve chunks sem erro

#### Scenario: Ramo sem termo pesquisável
- **WHEN** o título e a descrição do ramo estão vazios ou só têm palavras sem valor de busca, como artigos e preposições
- **THEN** a busca léxica devolve uma lista vazia sem erro e a fusão usa só a busca vetorial
