## MODIFIED Requirements

### Requirement: Anonimização e Proteção de Dados Pessoais
O sistema SHALL mascarar informações de dados pessoais sensíveis (PII) nos blocos de texto antes de qualquer operação de vetorização ou envio para provedores de LLM externos, mantendo os dados de reversão isolados exclusivamente nos metadados.

#### Scenario: Anonimização de documentos contendo PII
- **WHEN** blocos contendo CPFs, CNPJs ou nomes são processados
- **THEN** as ocorrências são substituídas por marcadores indexados e o mapa de reversão é armazenado apenas no metadado `presidio_mapping`

#### Scenario: Nome de pessoa em maiúsculas
- **WHEN** o documento traz um nome de pessoa com duas ou mais palavras escrito em maiúsculas, como o nome de autoria na capa de um anteprojeto
- **THEN** o nome é substituído por um marcador `<PERSON_n>` no texto do chunk, em `section_title` e em `section_path`

#### Scenario: Mesmo nome em outra caixa ou em outro trecho
- **WHEN** um nome de pessoa reconhecido em um trecho do documento aparece em outro chunk, em outra caixa ou em um título de seção
- **THEN** todas as ocorrências recebem o mesmo marcador `<PERSON_n>`, e o mapa de reversão devolve uma única forma do nome para esse marcador

#### Scenario: Nome de autoria nas referências
- **WHEN** um nome de pessoa reconhecido fora das referências aparece também na seção de referências
- **THEN** o nome é mascarado também na seção de referências

#### Scenario: Autores citados permanecem visíveis
- **WHEN** um autor aparece só na seção de referências, ou aparece no corpo só pelo sobrenome em uma citação
- **THEN** o nome do autor permanece no texto do chunk

#### Scenario: Expressões capitalizadas que não são nomes
- **WHEN** o modelo de linguagem marca como pessoa uma expressão de uma palavra, uma expressão cujas palavras o documento também usa em minúsculas ou uma expressão igual a um título numerado de seção
- **THEN** a expressão permanece no texto do chunk
