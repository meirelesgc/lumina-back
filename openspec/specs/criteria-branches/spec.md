# criteria-branches Specification

## Purpose
Define como a API cria, edita e devolve os ramos da árvore de critérios, incluindo a configuração que orienta a avaliação de cada ramo.

## Requirements

### Requirement: Marcação do Escopo de Seção do Ramo
O sistema SHALL guardar em cada ramo uma marcação de escopo de seção feita por quem configura a árvore: `SPECIFIC_SECTION` com o nome da seção esperada, `ENTIRE_DOCUMENT` ou `UNKNOWN` (sem marcação). A criação e a edição SHALL aceitar a marcação, e toda resposta que devolve um ramo SHALL trazê-la.

#### Scenario: Ramo criado com seção indicada
- **WHEN** o configurador cria um ramo com escopo `SPECIFIC_SECTION` e seção esperada "Metodologia"
- **THEN** a resposta traz o ramo com esse escopo e essa seção, e a consulta do ramo devolve os mesmos valores

#### Scenario: Ramo criado sem marcação
- **WHEN** o configurador cria um ramo só com título, descrição e taxonomia
- **THEN** o ramo fica com escopo `UNKNOWN` e sem seção esperada

#### Scenario: Ramo marcado como documento inteiro
- **WHEN** o configurador edita um ramo e envia o escopo `ENTIRE_DOCUMENT` sem seção esperada
- **THEN** o ramo passa a ter escopo `ENTIRE_DOCUMENT` e nenhuma seção esperada

#### Scenario: Remoção da marcação
- **WHEN** o configurador edita um ramo marcado e envia o escopo `UNKNOWN`
- **THEN** o ramo fica sem marcação e sem seção esperada

#### Scenario: Ramos existentes depois da migração
- **WHEN** a migração desta mudança roda sobre um banco com ramos já cadastrados
- **THEN** todos os ramos ficam com escopo `UNKNOWN` e sem seção esperada

### Requirement: Edição do Ramo sem os Campos da Marcação
Uma edição de ramo que omite os campos da marcação SHALL manter a marcação atual.

#### Scenario: Edição que omite a marcação
- **WHEN** o configurador edita o título de um ramo marcado com `SPECIFIC_SECTION` e não envia os campos da marcação
- **THEN** o ramo guarda o novo título e mantém o escopo e a seção esperada

### Requirement: Validação da Marcação
A API SHALL recusar com 422, sem alterar o ramo, uma marcação em que o escopo e a seção esperada não combinam: só `SPECIFIC_SECTION` leva seção esperada, e ela não pode ser vazia.

#### Scenario: Seção indicada sem nome
- **WHEN** a criação ou a edição envia `SPECIFIC_SECTION` sem seção esperada ou com seção esperada vazia
- **THEN** a API responde 422 e o ramo não muda

#### Scenario: Seção esperada com outro escopo
- **WHEN** a criação ou a edição envia uma seção esperada com escopo `ENTIRE_DOCUMENT` ou `UNKNOWN`
- **THEN** a API responde 422 e o ramo não muda

#### Scenario: Seção esperada sem escopo
- **WHEN** a edição envia uma seção esperada e omite o escopo
- **THEN** a API responde 422 e o ramo não muda

#### Scenario: Escopo inválido
- **WHEN** a criação ou a edição envia um escopo fora dos três valores aceitos
- **THEN** a API responde 422 e o ramo não muda

### Requirement: Escopo sem Classificação Automática
O sistema SHALL NOT classificar o escopo de seção de um ramo com modelos de linguagem.

#### Scenario: Criação e edição sem classificação automática
- **WHEN** o configurador cria um ramo ou edita o título ou a descrição dele
- **THEN** o sistema não chama um modelo de linguagem para classificar o escopo, e a marcação fica como o configurador enviou
