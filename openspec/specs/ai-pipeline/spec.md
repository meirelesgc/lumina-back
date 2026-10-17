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

### Requirement: Árvore de Seções e Vinculação aos Chunks
O sistema SHALL montar a árvore de seções do documento a partir dos títulos do Markdown extraído, sem chamadas a modelos de linguagem, e SHALL classificar o papel semântico de cada seção (resumo, introdução, metodologia etc.) por aliases de título e por posição. Cada chunk SHALL carregar o título da seção que o contém em `section_title`, o caminho de títulos em `section_path`, o papel em `section_role` e o prefixo `[título da seção] ` no conteúdo. Para cada seção, o sistema SHALL indexar um resumo (título e trecho inicial) marcado com `record_type=section_summary`, que a busca de chunks exclui.

#### Scenario: Atribuição de seção aos chunks
- **WHEN** o sistema gera os chunks de uma seção da árvore
- **THEN** cada chunk recebe `section_title`, `section_path` e `section_role` da seção e começa com `[título da seção] `

#### Scenario: Classificação de papel por alias
- **WHEN** o título de uma seção corresponde a um alias conhecido, como "Resumo" ou "Abstract"
- **THEN** a seção recebe o papel correspondente e `role_confidence` igual a `alias_match`

#### Scenario: Resumos de seção fora da busca de chunks
- **WHEN** o sistema indexa os chunks de um documento
- **THEN** o sistema indexa também um resumo por seção com `record_type=section_summary`, e a busca vetorial de chunks não retorna esses resumos

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

### Requirement: Critério de Aceite da Recuperação sobre Acervo Anotado
O sistema SHALL ter a recuperação de evidências validada contra um acervo versionado de PDFs. Cada PDF anotado SHALL ter um gabarito que reúne a árvore de critérios a avaliar e, para cada critério, os trechos esperados entre as evidências, com página, um trecho do texto do documento e, quando o trecho pertence a uma seção anotada, a seção. A validação SHALL usar o mesmo caminho de ingestão e de recuperação de uma avaliação real, com os mesmos embeddings. As métricas SHALL somar os resultados de todo o acervo e falhar abaixo de um piso registrado, que só sobe.

#### Scenario: Trecho anotado inexistente no documento indexado
- **WHEN** um trecho do gabarito não aparece no texto anonimizado dos chunks da página anotada e, quando o gabarito informa a seção, dessa seção
- **THEN** a validação do gabarito falha sem chamar modelos e aponta o documento, o critério e o trecho

#### Scenario: Seção anotada fora do gabarito de seções
- **WHEN** um trecho do gabarito cita uma seção que não está no gabarito de seções do mesmo documento
- **THEN** a validação do gabarito falha e aponta o documento, o critério e a seção

#### Scenario: Trecho fora das seções anotadas
- **WHEN** um trecho do gabarito não informa seção, como o título na capa
- **THEN** a validação do gabarito confere só a página, e o acerto de seção e página desse trecho depende só da página

#### Scenario: Evidência de outro documento
- **WHEN** a recuperação devolve, para um critério, uma evidência indexada a partir de outro documento do acervo
- **THEN** a validação falha e aponta o documento e o critério

#### Scenario: Métrica de recuperação abaixo do piso
- **WHEN** o recall de trechos, o acerto de seção e página, a precisão entre critérios ou o acerto do roteamento por seção, somados sobre o acervo, ficam abaixo do piso registrado da métrica
- **THEN** a validação falha e informa o placar por documento e por critério

#### Scenario: Métricas de recuperação no piso ou acima
- **WHEN** todas as métricas atingem os pisos registrados
- **THEN** a validação passa e informa o placar por documento e por critério, mesmo com trechos individuais não recuperados

#### Scenario: Critério sem evidência no documento
- **WHEN** o gabarito declara que o documento não atende um critério
- **THEN** a validação informa o que a recuperação devolveu para ele e o resultado do roteamento, sem contar o critério nas métricas com piso

### Requirement: Anonimização e Proteção de Dados Pessoais
O sistema SHALL mascarar informações de dados pessoais sensíveis (PII) nos blocos de texto antes de qualquer operação de vetorização ou envio para provedores de LLM externos, mantendo os dados de reversão isolados exclusivamente nos metadados.

#### Scenario: Anonimização de documentos contendo PII
- **WHEN** blocos contendo CPFs, CNPJs ou nomes são processados
- **THEN** as ocorrências são substituídas por marcadores indexados e o mapa de reversão é armazenado apenas no metadado `presidio_mapping`

### Requirement: Avaliação Estruturada de Critérios com Resolução de Citações
O sistema SHALL avaliar concorrentemente critérios normativos utilizando trechos recuperados do documento expandidos com os chunks vizinhos da mesma seção e página ($\pm 1$), retornando parecer técnico, nota no barema de 0 a 10, flag de atendimento e coordenadas visuais das evidências citadas. O parecer SHALL ser curto, em Markdown estruturado (listas ou tabela, sem parágrafos longos), seguindo um estilo de resposta sorteado de forma independente para cada critério, e SHALL conter sugestões de melhoria apenas para lacunas identificadas, limitadas a uma ação por lacuna.

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
O sistema SHALL persistir em disco os artefatos intermediários de processamento e o arquivo PDF anotado com as seções e fragmentos textuais (chunks) delimitados, organizados em diretórios específicos, exclusivamente quando a flag `DEBUG_INGESTION_AUDIT` estiver configurada como verdadeira nas configurações da aplicação.

#### Scenario: Ingestão de documento com auditoria desativada
- **WHEN** um documento PDF é processado pelo motor de ingestão com a flag `DEBUG_INGESTION_AUDIT` desativada (`False`)
- **THEN** o sistema executa todo o processamento, extração, árvore de seções e fatiamento em memória, sem criar diretórios ou persistir arquivos de auditoria no sistema de arquivos local

#### Scenario: Ingestão de documento com auditoria ativada
- **WHEN** um documento PDF é processado pelo motor de ingestão com a flag `DEBUG_INGESTION_AUDIT` ativada (`True`)
- **THEN** o sistema grava os artefatos nos subdiretórios do caminho configurado em `INGESTION_AUDIT_DIRECTORY`:
  - `01_raw_markdown/`: Markdown bruto extraído (`.md`) e mapeamento físico de páginas (`_pages.json`)
  - `02_sections_tree/`: Árvore de seções estruturada em JSON (`_sections.json`) e relatório legível em Markdown (`_sections.md`)
  - `03_chunks/`: Fragmentos textuais finais enriquecidos com retângulos de linha em JSON (`_chunks.json`) e prévia textual em Markdown (`_chunks.md`)
  - `04_annotated_pdfs/`: Arquivo PDF anotado visualmente (`_annotated.pdf`) com barras marginais identificando as seções por papel semântico e caixas destacando os chunks

### Requirement: Fusão de Consultas Expandidas por Reciprocal Rank Fusion
O sistema SHALL gerar, de forma assíncrona e versionada, formulações alternativas de consulta
para cada critério normativo (`branch`) e, quando existirem expansões ativas, SHALL fundir os
resultados da busca vetorial da consulta original com os resultados das expansões via
Reciprocal Rank Fusion antes de formatar o contexto enviado à avaliação estruturada.

#### Scenario: Critério sem expansões ativas
- **WHEN** um critério normativo não possui expansões de consulta ativas
- **THEN** o sistema recupera os chunks apenas pela consulta original, com resultado idêntico
  ao comportamento de busca vetorial de consulta única

#### Scenario: Critério com expansões ativas
- **WHEN** um critério normativo possui de 2 a 4 expansões de consulta ativas
- **THEN** o sistema executa a busca vetorial da consulta original e de cada expansão em
  paralelo, isolada pelo mesmo filtro de documento, e funde os resultados por Reciprocal Rank
  Fusion, mantendo o número final de chunks recuperados inalterado

#### Scenario: Regeneração de expansões não afeta avaliações já concluídas
- **WHEN** as expansões de consulta de um critério são regeneradas após uma avaliação já ter
  sido concluída
- **THEN** o snapshot de auditoria daquela avaliação preserva a versão de geração das expansões
  vigentes no momento em que foi realizada, sem ser afetado pela regeneração
