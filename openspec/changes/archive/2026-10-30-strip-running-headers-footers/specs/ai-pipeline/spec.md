## ADDED Requirements

### Requirement: Remoção de Cabeçalhos e Rodapés Corridos
O sistema SHALL tirar do texto dos chunks as linhas que se repetem no topo ou na base das páginas do PDF, como título corrido, autores, nome do periódico e número de página. O sistema SHALL manter o texto que aparece perto do topo ou da base de uma única página, como legenda de figura, e SHALL manter a primeira ocorrência de uma linha corrida que o layout não marca como cabeçalho ou rodapé. Os deslocamentos dos chunks no texto extraído SHALL continuar os mesmos.

#### Scenario: Título corrido nas páginas pares
- **WHEN** um PDF repete o título "DENGUE NO BRASIL: UMA REVISÃO SISTEMÁTICA" no cabeçalho das páginas 2 a 24
- **THEN** nenhum chunk dessas páginas contém o título
- **AND** o título do artigo continua no chunk da página 1

#### Scenario: Rodapé com número de página que muda
- **WHEN** um PDF repete o rodapé "Revista Foco |Curitiba (PR)| v.17.n.3|e4640| p.01-24 |2024" seguido do número da página em todas as páginas
- **THEN** nenhum chunk contém o rodapé nem o número de página

#### Scenario: Linha de autores marcada como texto comum
- **WHEN** um PDF repete a linha de autores no topo das páginas 2 a 27 e o layout a marca como texto comum
- **THEN** só os chunks da página 2, a primeira ocorrência, contêm a linha

#### Scenario: Legenda de figura marcada como rodapé
- **WHEN** a legenda "Figura 2 – Busca do SIMCC" aparece na base da página 9 e o layout a marca como rodapé
- **THEN** a legenda continua no chunk da página 9

#### Scenario: Linha repetida no meio da página
- **WHEN** a linha "Fonte: Criada pelos autores (2023)" se repete abaixo de várias figuras, longe do topo e da base
- **THEN** a linha continua nos chunks de cada página

#### Scenario: Documento sem linhas corridas
- **WHEN** um PDF de 6 páginas não repete nenhuma linha no topo nem na base
- **THEN** o sistema gera os mesmos chunks, com o mesmo texto, que gerava antes desta mudança

#### Scenario: Citação de um chunk do topo da página
- **WHEN** a avaliação cita o primeiro chunk de uma página que tinha cabeçalho corrido
- **THEN** os retângulos da citação cobrem o texto do chunk e não cobrem o cabeçalho

## MODIFIED Requirements

### Requirement: Critério de Aceite da Ingestão sobre Acervo Anotado
O sistema SHALL ser validado contra um acervo versionado de PDFs, em que cada PDF tem um gabarito com as seções e subseções esperadas (título, página e primeiras palavras do texto) e um gabarito com as linhas corridas que não podem chegar aos chunks e as linhas perto do topo ou da base que precisam ficar. A validação SHALL rodar sem chamadas a modelos de linguagem.

#### Scenario: Texto de seção anotada ausente dos chunks
- **WHEN** as primeiras palavras de uma seção anotada não aparecem no texto dos chunks do documento
- **THEN** a validação falha e aponta o documento e a seção

#### Scenario: Identificação de seções abaixo do piso
- **WHEN** a fração de seções anotadas que a ingestão identifica com título e página corretos, somada sobre todo o acervo, fica abaixo do piso registrado
- **THEN** a validação falha e informa o placar por documento

#### Scenario: Identificação de seções no piso ou acima
- **WHEN** essa fração atinge o piso registrado
- **THEN** a validação passa e informa o placar por documento, mesmo com seções individuais não identificadas

#### Scenario: Linha corrida anotada nos chunks
- **WHEN** uma linha corrida do gabarito aparece no texto dos chunks de uma página fora das páginas em que o gabarito a mantém
- **THEN** a validação falha e aponta o documento, a linha e as páginas

#### Scenario: Linha a manter ausente dos chunks
- **WHEN** uma linha que o gabarito manda manter não aparece no texto dos chunks da página anotada
- **THEN** a validação falha e aponta o documento, a linha e a página
