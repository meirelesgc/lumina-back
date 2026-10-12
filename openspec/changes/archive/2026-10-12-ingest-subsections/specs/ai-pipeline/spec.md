## ADDED Requirements

### Requirement: Cobertura Integral do Texto por Seções e Subseções
O sistema SHALL gerar chunks para o texto de todas as seções da árvore de seções do documento, em qualquer nível de hierarquia, na ordem de leitura. Cada chunk SHALL carregar o título da seção mais específica que o contém e o caminho completo de títulos até ela.

#### Scenario: Documento com subseções numeradas
- **WHEN** um PDF com a seção "2. Desenvolvimento" e as subseções "2.1" e "2.2" é ingerido
- **THEN** o texto de "2.1" e de "2.2" aparece nos chunks gerados
- **AND** os chunks de "2.2" trazem "2.2 ..." como título de seção e "2. Desenvolvimento > 2.2 ..." como caminho

#### Scenario: Seção filha sem numeração
- **WHEN** a árvore de seções coloca "ABSTRACT" como filha de outra seção
- **THEN** o texto de "ABSTRACT" aparece nos chunks gerados, com "ABSTRACT" como título de seção

#### Scenario: Documento sem subseções
- **WHEN** um PDF cuja árvore só tem seções de primeiro nível é ingerido
- **THEN** o sistema gera os mesmos chunks, com os mesmos títulos e a mesma ordem, que gerava antes desta mudança

### Requirement: Critério de Aceite da Ingestão sobre Acervo Anotado
O sistema SHALL ser validado contra um acervo versionado de PDFs, em que cada PDF tem um gabarito com as seções e subseções esperadas (título, página e primeiras palavras do texto). A validação SHALL rodar sem chamadas a modelos de linguagem.

#### Scenario: Texto de seção anotada ausente dos chunks
- **WHEN** as primeiras palavras de uma seção anotada não aparecem no texto dos chunks do documento
- **THEN** a validação falha e aponta o documento e a seção

#### Scenario: Identificação de seções abaixo do piso
- **WHEN** a fração de seções anotadas que a ingestão identifica com título e página corretos, somada sobre todo o acervo, fica abaixo do piso registrado
- **THEN** a validação falha e informa o placar por documento

#### Scenario: Identificação de seções no piso ou acima
- **WHEN** essa fração atinge o piso registrado
- **THEN** a validação passa e informa o placar por documento, mesmo com seções individuais não identificadas
