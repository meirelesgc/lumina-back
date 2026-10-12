## ADDED Requirements

### Requirement: Detecção de Títulos de Seção
O sistema SHALL reconhecer como título de seção, além dos títulos do Markdown extraído, um rótulo em negrito seguido de dois-pontos no início de uma linha, quando o rótulo pertence à lista de nomes de seção conhecidos. O texto que segue o rótulo na mesma linha SHALL pertencer à seção do rótulo. Ao juntar títulos vizinhos quebrados em mais de uma linha, o sistema SHALL manter separado um título que tem numeração própria ou que é um nome de seção conhecido.

#### Scenario: Rótulo conhecido na mesma linha do texto
- **WHEN** o Markdown extraído tem a linha `**Funding:** This research was supported by...`
- **THEN** a árvore tem a seção "Funding"
- **AND** o texto "This research was supported by..." aparece nos chunks dessa seção

#### Scenario: Rótulo fora da lista de nomes conhecidos
- **WHEN** um resumo estruturado tem as linhas `**Objetivo**: ...` e `**Metodologia**: ...`
- **THEN** o sistema não cria seções "Objetivo" nem "Metodologia" e o texto continua na seção do resumo

#### Scenario: Título numerado logo após outro título
- **WHEN** o título "2. Desenvolvimento" vem seguido, sem texto entre eles, do título "2.1 Agente Etiológico"
- **THEN** a árvore tem a seção "2. Desenvolvimento" com a subseção "2.1 Agente Etiológico"

#### Scenario: Nome de seção conhecido logo após outro título
- **WHEN** o título "DOI: 10.54751/..." vem seguido, sem texto entre eles, do título "RESUMO"
- **THEN** a árvore tem uma seção "RESUMO" separada da seção do DOI

#### Scenario: Título quebrado em duas linhas
- **WHEN** o título "1.0. DO OBJETO:" vem seguido, sem texto entre eles, do título sem numeração "CONTRATAÇÃO DE EMPRESA ESPECIALIZADA"
- **THEN** o sistema junta os dois em um único título "1.0. DO OBJETO: CONTRATAÇÃO DE EMPRESA ESPECIALIZADA"
