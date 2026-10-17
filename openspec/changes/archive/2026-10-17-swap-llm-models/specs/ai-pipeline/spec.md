## ADDED Requirements

### Requirement: Leitura do Texto da Resposta do Modelo
O sistema SHALL extrair o texto da resposta do modelo de linguagem da mesma forma quando o conteúdo vem como texto simples e quando vem como lista de blocos de conteúdo. Pareceres, sínteses e respostas do chat SHALL conter apenas o texto gerado, sem a estrutura dos blocos.

#### Scenario: Parecer com resposta em blocos
- **WHEN** o modelo devolve o parecer de um critério como lista de blocos de conteúdo com um JSON válido no texto
- **THEN** o sistema registra o veredito, a nota, o parecer e as citações desse JSON, sem erro de validação de schema

#### Scenario: Parecer com resposta em texto simples
- **WHEN** o modelo devolve o parecer de um critério como texto simples com um JSON válido
- **THEN** o sistema registra o veredito, a nota, o parecer e as citações desse JSON

#### Scenario: Síntese e chat com resposta em blocos
- **WHEN** o modelo devolve a síntese executiva ou a resposta do chat como lista de blocos de conteúdo
- **THEN** o sistema grava ou devolve apenas o texto gerado
