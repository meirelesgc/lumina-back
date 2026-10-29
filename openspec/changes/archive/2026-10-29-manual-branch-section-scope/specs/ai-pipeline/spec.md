## MODIFIED Requirements

### Requirement: Seleção de Seções pelo Sumário do Documento
O sistema SHALL escolher o contexto de cada critério a partir do sumário do documento, que lista cada seção com identificador, caminho de títulos, páginas, tamanho estimado e o início do texto. O escopo de cada critério SHALL vir da marcação do ramo na árvore de critérios. Para critérios com seção indicada ou sem marcação, um seletor SHALL pedir seções pelo identificador, ler o texto integral delas e decidir se o conteúdo basta, pedir outras seções ou concluir que o conteúdo não existe no documento, em no máximo 3 rodadas. Com seção indicada, o seletor SHALL receber o nome da seção como dica. Critérios marcados como documento inteiro SHALL receber todas as seções sem passar pelo seletor. Cada veredito SHALL registrar a seleção que o gerou, com o escopo e a seção indicada.

#### Scenario: Critério de seção com conteúdo encontrado
- **WHEN** um critério de escopo de seção é avaliado e o seletor indica que as seções lidas bastam
- **THEN** o avaliador recebe o texto integral dessas seções com os identificadores de chunk, e o veredito registra as seções, o motivo, as rodadas e os tokens

#### Scenario: Critério com seção indicada
- **WHEN** um critério cujo ramo está marcado com a seção indicada "Metodologia" é avaliado
- **THEN** o seletor recebe "Metodologia" como dica, e o veredito registra o escopo `SPECIFIC_SECTION` e a seção indicada

#### Scenario: Critério sem marcação
- **WHEN** um critério cujo ramo não tem marcação é avaliado
- **THEN** o seletor escolhe as seções sem dica, e o veredito registra o escopo `UNKNOWN`

#### Scenario: Critério de documento inteiro
- **WHEN** um critério cujo ramo está marcado como documento inteiro é avaliado
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
