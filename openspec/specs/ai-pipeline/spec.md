# ai-pipeline Specification

## Purpose
Define a arquitetura modular e os comportamentos esperados para o pipeline de processamento, extração de texto, anonimização LGPD, indexação vetorial e avaliação estruturada de documentos por inteligência artificial.

## Requirements

### Requirement: Extração de Texto e Chunking por Seção e Página
O sistema SHALL extrair o texto de arquivos PDF em Markdown, página a página, com um mapa de páginas que registra o deslocamento de cada página no texto completo. O sistema SHALL cortar o texto de cada seção nos limites de página, de modo que cada chunk pertença a uma única página, e SHALL dividir os trechos com mais de 1000 caracteres em chunks de até 1000 caracteres, com sobreposição de 150. Cada chunk SHALL carregar `chunk_id` no formato `chunk_{página}_{índice na página}`, a página `page` (base 0), os deslocamentos `char_start` e `char_end` e os retângulos `rects` das linhas que ocupa no PDF original.

#### Scenario: Extração de documento PDF com coordenadas
- **WHEN** um documento PDF válido é processado pela etapa de extração
- **THEN** o sistema emite chunks com `chunk_id`, `page`, texto sanitizado e os retângulos `rects` das linhas correspondentes no documento original

#### Scenario: Seção que atravessa páginas
- **WHEN** o texto de uma seção começa em uma página e termina na seguinte
- **THEN** o sistema gera chunks separados para cada página, e nenhum chunk mistura texto das duas

#### Scenario: Trecho maior que o limite
- **WHEN** o trecho de uma seção em uma página passa de 1000 caracteres
- **THEN** o sistema divide o trecho em chunks de até 1000 caracteres, com 150 caracteres de sobreposição entre chunks vizinhos

#### Scenario: Rejeição de formatos não suportados
- **WHEN** um arquivo com extensão diferente de PDF é fornecido na extração
- **THEN** o sistema SHALL rejeitar o processamento levantando erro de tipo de arquivo não suportado

### Requirement: Árvore de Seções e Metadados dos Chunks
O sistema SHALL montar a árvore de seções do documento a partir dos títulos do Markdown extraído, sem chamadas a modelos de linguagem, e SHALL classificar o papel semântico de cada seção (resumo, introdução, metodologia etc.) por aliases de título e por posição. Cada chunk SHALL carregar o título da seção que o contém em `section_title`, o caminho de títulos em `section_path`, o papel em `section_role` e o prefixo `[título da seção] ` no conteúdo.

#### Scenario: Atribuição de seção aos chunks
- **WHEN** o sistema gera os chunks de uma seção da árvore
- **THEN** cada chunk recebe `section_title`, `section_path` e `section_role` da seção e começa com `[título da seção] `

#### Scenario: Classificação de papel por alias
- **WHEN** o título de uma seção corresponde a um alias conhecido, como "Resumo" ou "Abstract"
- **THEN** a seção recebe o papel correspondente e `role_confidence` igual a `alias_match`

### Requirement: Indexação Apenas de Chunks
A ingestão SHALL indexar na base vetorial apenas os chunks do documento.

#### Scenario: Indexação só de chunks
- **WHEN** o sistema indexa um documento
- **THEN** a base vetorial recebe os chunks do documento e nenhum resumo de seção

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

### Requirement: Validação dos Gabaritos do Acervo Anotado
Cada PDF anotado SHALL ter um gabarito que reúne a árvore de critérios a avaliar e, para cada critério, os trechos esperados, com página, um trecho do texto do documento e, quando o trecho pertence a uma seção anotada, a seção. A suíte padrão SHALL validar o gabarito sem chamar modelos.

#### Scenario: Trecho anotado inexistente no documento indexado
- **WHEN** um trecho do gabarito não aparece no texto anonimizado dos chunks da página anotada e, quando o gabarito informa a seção, dessa seção
- **THEN** a validação do gabarito falha sem chamar modelos e aponta o documento, o critério e o trecho

#### Scenario: Seção anotada fora do gabarito de seções
- **WHEN** um trecho do gabarito cita uma seção que não está no gabarito de seções do mesmo documento
- **THEN** a validação do gabarito falha e aponta o documento, o critério e a seção

#### Scenario: Trecho fora das seções anotadas
- **WHEN** um trecho do gabarito não informa seção, como o título na capa
- **THEN** a validação do gabarito confere só a página

### Requirement: Recuperação Híbrida do Chat
O chat SHALL fundir a busca vetorial com uma busca léxica sobre os chunks do documento da conversa. A busca léxica SHALL aceitar chunks com qualquer termo da mensagem e pôr antes os que têm mais ocorrências dos termos em relação ao próprio tamanho.

#### Scenario: Mensagem de várias palavras sem chunk que tenha todas
- **WHEN** a mensagem tem várias palavras e nenhum chunk do documento contém todas elas
- **THEN** a busca léxica devolve os chunks que contêm algum termo da mensagem

#### Scenario: Chunk longo com termos repetidos
- **WHEN** um chunk curto e um chunk longo contêm os termos da mensagem e o chunk longo repete esses termos em meio a muito texto sem relação
- **THEN** a busca léxica põe o chunk curto antes do longo

#### Scenario: Chunks de outro documento
- **WHEN** outro documento indexado contém os termos da mensagem
- **THEN** a busca léxica não devolve esses chunks

#### Scenario: Mensagem com caracteres de sintaxe de busca
- **WHEN** a mensagem contém símbolos como `&`, `|`, `!`, `:`, `(` ou aspas
- **THEN** a busca léxica trata os símbolos como texto e devolve chunks sem erro

#### Scenario: Mensagem sem termo pesquisável
- **WHEN** a mensagem está vazia ou só tem palavras sem valor de busca, como artigos e preposições
- **THEN** a busca léxica devolve uma lista vazia sem erro e a fusão usa só a busca vetorial

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

### Requirement: Critério de Aceite da Seleção de Seções sobre Acervo Anotado
A seleção de seções SHALL ser validada contra o acervo anotado de recuperação. O recall de trechos SHALL contar os trechos anotados presentes no contexto enviado ao avaliador. O acerto de veredicto SHALL comparar o `fulfilled` da avaliação com o anotado, e ramos sem evidência anotada SHALL contar como não contemplados. As métricas SHALL somar o acervo inteiro e falhar abaixo de um piso registrado, que só sobe.

#### Scenario: Recall da seleção abaixo do piso
- **WHEN** a fração de trechos anotados presentes no contexto selecionado, somada sobre o acervo, fica abaixo do piso registrado
- **THEN** a validação falha e informa o placar por documento e por critério, com as seções escolhidas e as rodadas

#### Scenario: Acerto de veredicto abaixo do piso
- **WHEN** a fração de critérios cujo `fulfilled` coincide com o anotado fica abaixo do piso registrado
- **THEN** a validação falha e informa os acertos e erros por documento e por critério

#### Scenario: Conclusão de inexistência errada
- **WHEN** o seletor conclui que o conteúdo não existe para um critério que tem evidência anotada
- **THEN** o placar conta o caso como erro de inexistência e o lista no relatório

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

### Requirement: Síntese Executiva Consolidada
O sistema SHALL sintetizar os resultados gerais da avaliação com base nos critérios de maior e menor pontuação, particionando o texto em seções de saudação, pontos atendidos, pontos a aprimorar e orientação final. A saudação SHALL ter uma única frase, as seções SHALL ser escritas em listas curtas em Markdown seguindo um estilo sorteado por síntese, e os títulos `# Pontos atendidos`, `# Pontos a aprimorar` e `# Orientação final` SHALL ser mantidos literalmente.

#### Scenario: Geração da síntese executiva
- **WHEN** a avaliação de todos os critérios da árvore é finalizada
- **THEN** o sistema gera a síntese executiva estruturada e a salva no resumo da release

#### Scenario: Particionamento preservado em qualquer estilo
- **WHEN** a síntese é gerada com qualquer um dos estilos de síntese disponíveis
- **THEN** o texto contém os três títulos de seção fixos e o particionamento em saudação, pontos atendidos, pontos a aprimorar e orientação final continua funcionando

### Requirement: Auditoria e Exportação Estruturada de Ingestão de Documentos
O sistema SHALL persistir em disco os artefatos intermediários de processamento, o arquivo PDF anotado com as seções e fragmentos textuais (chunks) delimitados, o sumário do documento e a seleção de seções de cada critério, organizados em diretórios específicos, exclusivamente quando a flag `DEBUG_INGESTION_AUDIT` estiver configurada como verdadeira nas configurações da aplicação.

#### Scenario: Ingestão de documento com auditoria desativada
- **WHEN** um documento PDF é processado pelo motor de ingestão com a flag `DEBUG_INGESTION_AUDIT` desativada (`False`)
- **THEN** o sistema executa todo o processamento, extração, árvore de seções, fatiamento e seleção de seções em memória, sem criar diretórios ou persistir arquivos de auditoria no sistema de arquivos local

#### Scenario: Ingestão de documento com auditoria ativada
- **WHEN** um documento PDF é processado pelo motor de ingestão com a flag `DEBUG_INGESTION_AUDIT` ativada (`True`)
- **THEN** o sistema grava os artefatos nos subdiretórios do caminho configurado em `INGESTION_AUDIT_DIRECTORY`:
  - `01_raw_markdown/`: Markdown bruto extraído (`.md`) e mapeamento físico de páginas (`_pages.json`)
  - `02_sections_tree/`: Árvore de seções estruturada em JSON (`_sections.json`) e relatório legível em Markdown (`_sections.md`)
  - `03_chunks/`: Fragmentos textuais finais enriquecidos com retângulos de linha em JSON (`_chunks.json`) e prévia textual em Markdown (`_chunks.md`)
  - `04_annotated_pdfs/`: Arquivo PDF anotado visualmente (`_annotated.pdf`) com barras marginais identificando as seções por papel semântico e caixas destacando os chunks

#### Scenario: Seleção de seções com auditoria ativada
- **WHEN** os critérios de uma release são avaliados com a flag `DEBUG_INGESTION_AUDIT` ativada (`True`)
- **THEN** o sistema grava o sumário do documento, exatamente como o seletor o recebe, em `05_outline/<documento>.md`, e, para cada critério, as rodadas do seletor, o contexto enviado ao avaliador e o veredito em `06_selection/<documento>/<critério>.md`

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
