## ADDED Requirements

### Requirement: Fusão de Consultas Expandidas por Reciprocal Rank Fusion
O sistema SHALL gerar, de forma assíncrona e versionada, formulações alternativas de consulta
para cada critério normativo (`branch`) e, quando existirem expansões ativas, SHALL fundir os
resultados da busca vetorial da consulta original com os resultados das expansões via
Reciprocal Rank Fusion antes de formatar o contexto enviado à avaliação estruturada.

#### Scenario: Critério sem expansões ativas
- **WHEN** um critério normativo não possui expansões de consulta ativas
- **THEN** o sistema recupera os chunks apenas pela consulta original, com resultado idêntico
  ao comportamento de busca vetorial de consulta única

#### Scenario: Critério com expansões ativas
- **WHEN** um critério normativo possui de 2 a 4 expansões de consulta ativas
- **THEN** o sistema executa a busca vetorial da consulta original e de cada expansão em
  paralelo, isolada pelo mesmo filtro de documento, e funde os resultados por Reciprocal Rank
  Fusion, mantendo o número final de chunks recuperados inalterado

#### Scenario: Regeneração de expansões não afeta avaliações já concluídas
- **WHEN** as expansões de consulta de um critério são regeneradas após uma avaliação já ter
  sido concluída
- **THEN** o snapshot de auditoria daquela avaliação preserva a versão de geração das expansões
  vigentes no momento em que foi realizada, sem ser afetado pela regeneração
