## MODIFIED Requirements

### Requirement: Avaliação Estruturada de Critérios com Resolução de Citações
O sistema SHALL avaliar concorrentemente critérios normativos utilizando trechos recuperados do documento com expansão de margem ($\pm 2$), retornando parecer técnico, nota no barema de 0 a 10, flag de atendimento e coordenadas visuais das evidências citadas. O parecer SHALL ser curto, em Markdown estruturado (listas ou tabela, sem parágrafos longos), seguindo um estilo de resposta sorteado de forma independente para cada critério, e SHALL conter sugestões de melhoria apenas para lacunas identificadas, limitadas a uma ação por lacuna.

#### Scenario: Avaliação de critério normativo com evidência no documento
- **WHEN** um critério normativo é avaliado contra trechos recuperados
- **THEN** a resposta contém nota de 0 a 10, parecer fundamentado, e os `chunk_id` citados são resolvidos em retângulos físicos `rects` para destaque visual no visualizador de PDF

#### Scenario: Detecção de alucinação de citações
- **WHEN** o modelo de linguagem cita um identificador de bloco inexistente nos trechos fornecidos
- **THEN** o sistema sinaliza a citação como alucinação e registra a métrica na telemetria de auditoria

#### Scenario: Estilo de resposta sorteado por critério
- **WHEN** os critérios de uma release são enviados para avaliação
- **THEN** cada critério recebe, de forma independente, um estilo de resposta sorteado entre os estilos de parecer disponíveis (Veredito + listas, Checklist, Tabela, Resumo + tópicos), mantendo inalterados o barema, as regras de citação e o formato JSON de saída

#### Scenario: Estilo mantido nas retentativas
- **WHEN** a avaliação em lote de uma release é repetida por falha transitória
- **THEN** cada critério é reavaliado com o mesmo estilo sorteado na primeira tentativa

#### Scenario: Critério integralmente atendido
- **WHEN** o modelo conclui que o critério é atendido integralmente
- **THEN** o parecer apresenta apenas a situação e as evidências, sem sugestões de melhoria

#### Scenario: Critério parcialmente atendido ou não atendido
- **WHEN** o modelo identifica lacunas no atendimento do critério
- **THEN** o parecer lista as lacunas e propõe no máximo uma ação curta por lacuna

### Requirement: Síntese Executiva Consolidada
O sistema SHALL sintetizar os resultados gerais da avaliação com base nos critérios de maior e menor pontuação, particionando o texto em seções de saudação, pontos atendidos, pontos a aprimorar e orientação final. A saudação SHALL ter uma única frase, as seções SHALL ser escritas em listas curtas em Markdown seguindo um estilo sorteado por síntese, e os títulos `# Pontos atendidos`, `# Pontos a aprimorar` e `# Orientação final` SHALL ser mantidos literalmente.

#### Scenario: Geração da síntese executiva
- **WHEN** a avaliação de todos os critérios da árvore é finalizada
- **THEN** o sistema gera a síntese executiva estruturada e a salva no resumo da release

#### Scenario: Particionamento preservado em qualquer estilo
- **WHEN** a síntese é gerada com qualquer um dos estilos de síntese disponíveis
- **THEN** o texto contém os três títulos de seção fixos e o particionamento em saudação, pontos atendidos, pontos a aprimorar e orientação final continua funcionando
