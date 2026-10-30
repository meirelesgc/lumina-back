## ADDED Requirements

### Requirement: Frases Citáveis por Chunk
Na ingestão, o sistema SHALL dividir o texto de cada chunk em frases numeradas a partir de 1, na ordem de leitura. Cada frase SHALL registrar sua posição no texto anonimizado do chunk e os retângulos das linhas que ocupa no PDF original. Abreviações não SHALL encerrar frase, e fragmentos curtos SHALL se juntar à frase seguinte.

#### Scenario: Chunk com várias frases
- **WHEN** um chunk com três frases é ingerido
- **THEN** o chunk traz as frases 1, 2 e 3, cada uma com a posição no texto e retângulos próprios

#### Scenario: Abreviação no meio da frase
- **WHEN** o texto traz "Segundo Silva et al. a incidência caiu."
- **THEN** o sistema mantém o trecho em uma única frase

#### Scenario: Fragmento curto
- **WHEN** a divisão gera um fragmento curto, como o rótulo de uma linha de tabela
- **THEN** o fragmento pertence à frase seguinte, e a última frase do chunk absorve um fragmento final

#### Scenario: Texto integral coberto pelas frases
- **WHEN** um chunk é ingerido
- **THEN** todo texto do chunk pertence a exatamente uma frase, na ordem do chunk

#### Scenario: Frase sem retângulo localizado
- **WHEN** o sistema não localiza no PDF as linhas de uma frase
- **THEN** a frase fica com a lista de retângulos vazia e a ingestão continua

### Requirement: Dados Pessoais nas Frases
As frases SHALL referenciar o texto anonimizado do chunk e não SHALL guardar cópia do texto original nos metadados. Uma entidade anonimizada SHALL pertencer inteira a uma única frase.

#### Scenario: Frase com nome de pessoa
- **WHEN** uma frase contém um nome de pessoa que a anonimização substitui por `<PERSON_n>`
- **THEN** o texto da frase no contexto e em `text_snippet` traz `<PERSON_n>`, e os metadados da frase não trazem o nome

#### Scenario: Entidade na fronteira entre frases
- **WHEN** uma entidade anonimizada atravessa a fronteira entre duas frases, como "Dr. Fulano"
- **THEN** a fronteira passa para depois do marcador, e os deslocamentos das frases continuam válidos no texto anonimizado

### Requirement: Citação por Frase
A avaliação e o chat SHALL apresentar ao modelo as frases de cada chunk marcadas por número, e o modelo SHALL citar o `chunk_id` com os números das frases que fundamentam a resposta. Cada citação válida SHALL gerar uma referência com o `chunk_id`, a página, os retângulos das frases citadas e o texto delas em `text_snippet`.

#### Scenario: Citação de uma frase
- **WHEN** o modelo cita a frase 2 do chunk `chunk_3_1`
- **THEN** a referência traz `chunk_id` igual a `chunk_3_1`, a página do chunk, só os retângulos da frase 2 e o texto da frase 2 em `text_snippet`

#### Scenario: Citação de frases vizinhas
- **WHEN** o modelo cita as frases 2, 3 e 4 do mesmo chunk em uma citação
- **THEN** o sistema gera uma única referência com os retângulos das três frases na ordem de leitura

#### Scenario: Citações diferentes no mesmo chunk
- **WHEN** o modelo cita a frase 1 e, em outra citação, a frase 5 do mesmo chunk
- **THEN** o sistema gera duas referências, cada uma com os retângulos da sua frase

#### Scenario: Citação repetida
- **WHEN** o modelo repete uma citação com o mesmo chunk e as mesmas frases
- **THEN** o sistema gera uma única referência

#### Scenario: Número de frase inexistente
- **WHEN** o modelo cita frases 2 e 40 de um chunk que tem 6 frases
- **THEN** a referência usa a frase 2, ignora a 40 e o sistema registra o número inválido no log

#### Scenario: Citação sem frase válida
- **WHEN** o modelo cita um chunk existente sem nenhum número de frase válido
- **THEN** a referência traz os retângulos do chunk inteiro

#### Scenario: Frase citada sem retângulo
- **WHEN** nenhuma frase citada tem retângulo localizado
- **THEN** a referência traz os retângulos do chunk inteiro

#### Scenario: Chunk indexado antes da mudança
- **WHEN** o chat recupera um chunk indexado sem frases numeradas
- **THEN** o contexto mostra o chunk sem marcadores, e uma citação desse chunk traz os retângulos do chunk inteiro

#### Scenario: Referência já salva
- **WHEN** alguém consulta uma avaliação feita antes da mudança
- **THEN** o sistema devolve as referências salvas sem alteração

#### Scenario: Formato da referência preservado
- **WHEN** uma referência por frase é devolvida
- **THEN** ela valida no mesmo schema de `DocumentReference` usado antes da mudança

### Requirement: Critério de Aceite das Frases sobre Acervo Anotado
O sistema SHALL validar as frases contra o acervo anotado sem chamar modelos de linguagem. Texto fora das frases ou frases fora da ordem SHALL falhar com tolerância zero. A fração de frases com retângulos e a redução de linhas em relação ao chunk SHALL falhar abaixo de um piso registrado, que só sobe. A precisão das citações do modelo SHALL ser medida à parte com modelos reais.

#### Scenario: Texto de chunk fora das frases
- **WHEN** algum trecho do texto de um chunk do acervo não pertence a nenhuma frase
- **THEN** a validação falha e aponta o documento e o chunk

#### Scenario: Métrica de frases abaixo do piso
- **WHEN** a fração de frases com retângulos ou a redução de linhas, somadas sobre o acervo, ficam abaixo do piso registrado
- **THEN** a validação falha e informa o placar por documento

#### Scenario: Citações do modelo sobre o gabarito
- **WHEN** a avaliação com modelos reais roda sobre os ramos com trechos anotados
- **THEN** o relatório informa, por documento e por critério, se as frases citadas contêm o trecho anotado e quantas linhas a referência destaca em relação ao chunk

## MODIFIED Requirements

### Requirement: Avaliação Estruturada de Critérios com Resolução de Citações
O sistema SHALL avaliar concorrentemente critérios normativos utilizando as seções do documento escolhidas pela seleção de seções, com o texto integral de cada seção, os identificadores de chunk e os números das frases, retornando parecer técnico, nota no barema de 0 a 10, flag de atendimento e coordenadas visuais das evidências citadas. O parecer SHALL ser curto, em Markdown estruturado (listas ou tabela, sem parágrafos longos), seguindo um estilo de resposta sorteado de forma independente para cada critério, e SHALL conter sugestões de melhoria apenas para lacunas identificadas, limitadas a uma ação por lacuna.

#### Scenario: Avaliação de critério normativo com evidência no documento
- **WHEN** um critério normativo é avaliado contra as seções selecionadas
- **THEN** a resposta contém nota de 0 a 10, parecer fundamentado, e as frases citadas são resolvidas em retângulos físicos `rects` para destaque visual no visualizador de PDF

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

#### Scenario: Todo critério recebe veredito
- **WHEN** uma release é avaliada
- **THEN** cada critério da árvore recebe um veredito, inclusive os que o seletor conclui não existirem no documento
