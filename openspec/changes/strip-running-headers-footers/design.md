## Context

`extract_raw_markdown_and_pages` recebe do `pymupdf4llm` o markdown de cada página e as caixas de layout (`class`, `bbox` e `pos`, o intervalo da caixa no markdown da página). Em seguida junta espaços e tabulações com `re.sub(r'[ \t]+', ' ', ...)`, monta o `page_map` com o `char_start` de cada página e concatena as páginas. Seções, chunks e retângulos leem esse texto concatenado. `positioning.py` já ignora as caixas `page-header`, `page-footer` e `picture` ao calcular os retângulos, mas o texto dessas caixas continua no markdown e chega aos chunks.

Medições feitas no planejamento sobre os quatro PDFs do acervo:

| Documento | Páginas | Linhas corridas | Chunks com linha corrida hoje |
| :--- | ---: | :--- | ---: |
| `dengue_no_brasil.pdf` | 24 | rodapé do periódico e número (`page-footer`), título (`page-header`, páginas pares), autores (`text`, páginas ímpares) | 49 de 91 |
| `recuperando_especialistas_renovaveis_pln_ueba.pdf` | 27 | rodapé do periódico e número (`page-footer`), autores com título (`text`, páginas 2 a 27) | 53 de 94 |
| `smart_tech_microgrids.pdf` | 20 | "Energies 2025, 18, 2676" e "N of 20" (`page-header`) | 21 de 119 |
| `estrategias_teste_software_llm_judge_hitl.pdf` | 6 | nenhuma | 0 de 21 |

Em dois documentos o layout marca a linha de autores como `text`. O layout também marca como `page-footer` caixas que aparecem uma única vez e são conteúdo: as legendas "Figura 2" e "Figura 3" do recuperando e "SALVADOR 2026" na capa do anteprojeto.

O `pos` das caixas aponta para o markdown antes de juntar os espaços. Em 30 das 255 caixas perto do topo ou da base, o intervalo no texto final está deslocado alguns caracteres. Na página 9 da dengue, o intervalo de uma caixa começa no "m" de "Em 2008".

## Goals / Non-Goals

**Goals:**
- Tirar as linhas corridas antes da árvore de seções, para que nem os títulos falsos nem os chunks as vejam.
- Manter os deslocamentos atuais do texto extraído, das caixas e dos chunks.
- Validar contra o acervo com gabaritos escritos à mão, sem IA.

**Non-Goals:**
- Corrigir o deslocamento que já existe entre o `pos` das caixas e o texto depois de juntar espaços. Ele afeta os retângulos de citação hoje e fica na issue #43.
- Dar retângulo às legendas que o layout marca como rodapé. `positioning.py` continua ignorando `page-header` e `page-footer` (issue #43).
- Tratar notas de rodapé (`footnote`), como as afiliações dos autores.

## Decisions

### Detectar pela classe do layout e pela repetição na faixa

Uma caixa é candidata quando a classe é `page-header` ou `page-footer`, ou quando o centro do `bbox` fica nos 12% de cima ou de baixo da altura da página. Caixas `picture` ficam de fora. A chave de cada caixa é o texto dela sem marcação Markdown e HTML, com dígitos trocados por `#`, espaços juntos e sem diferença de caixa. O sistema conta em quantas páginas cada chave aparece entre as candidatas.

- Caixa `page-header` ou `page-footer`: o sistema apaga quando a chave aparece em 2 páginas ou mais. Isso cobre o documento curto, em que não há repetição suficiente para a regra de texto, e mantém as legendas e a capa, que aparecem uma vez.
- Outra caixa na faixa: o sistema apaga quando a chave aparece em pelo menos 3 páginas e em 30% das páginas do documento. A ocorrência da menor página fica no texto. Os cabeçalhos alternados da dengue aparecem em 50% das páginas.

Trocar dígitos por `#` faz o número de página e "N of 20" contarem como uma linha só. A restrição à faixa mantém "Fonte: Criada pelos autores (2023)", que se repete 7 vezes no meio das páginas do recuperando.

Alternativas avaliadas na exploração: só a classe do layout (deixa a linha de autores em dois documentos) e só a repetição na faixa (não cobre documentos curtos). A primeira versão do plano apagava `page-header` e `page-footer` sem contar repetição e apagaria as legendas.

### Apagar no markdown bruto da página, antes de juntar espaços

`extract_raw_markdown_and_pages` passa a ler todas as páginas do `pymupdf4llm`, decidir as caixas corridas e só então montar o texto. Para cada caixa corrida, troca os caracteres de `raw_text[pos[0]:pos[1]]` por `\n`, antes do `re.sub` de espaços. Como o `pos` aponta para o texto bruto, o intervalo apagado coincide com a caixa.

O caractere de troca é `\n` porque o `re.sub` junta só espaços e tabulações. Com espaços, o intervalo apagado viraria um único espaço, e todas as caixas seguintes da página andariam para trás o tamanho do cabeçalho. Com `\n`, o texto da página tem o mesmo tamanho de hoje, e o `page_map` e as caixas continuam com os mesmos números. O chunking já tira as quebras das pontas (`strip`) e junta três ou mais quebras (`clean_whitespace`).

Alternativas:
- Apagar no texto final pelo `pos`: rejeitada pela medição de deslocamento, que comeria letras do corpo.
- Remover o trecho e recalcular `char_start`, `pos` e linhas: muda todos os deslocamentos e mexe em seções, chunks e retângulos ao mesmo tempo.
- Filtrar só no chunking: a árvore de seções continuaria lendo os cabeçalhos como títulos.

A detecção e a máscara ficam em funções puras em `extraction.py`, testadas sem PDF. `extract_raw_markdown_and_pages` só as chama.

### Marcar as caixas apagadas no `page_map`

Cada caixa apagada ganha `'running': True` no `page_map`. `char_range_to_blocks` passa a ignorar essas caixas, além das classes que já ignora. Sem a marca, uma caixa `text` apagada (a linha de autores) entraria no cálculo do primeiro chunk da página, e `refine_block_to_line_rects`, sem tokens para alinhar, devolveria o `bbox` inteiro do cabeçalho como retângulo da citação.

### Gabarito `<nome>.running.yaml` e teste sobre o acervo

Jornada: o analista envia uma revisão sistemática e avalia um ramo que menciona "Revisão Sistemática". Ele espera que os trechos recuperados tragam conteúdo do documento e que o destaque da citação marque o trecho citado. A recuperação só enxerga o texto dos chunks, então o teste fica na extração, a camada mais barata que prova o comportamento, como no teste de seções.

O gabarito fica ao lado do PDF, no formato de `tests/fixtures/documents/running_template.yaml`: `running_lines` (com `text` e `keep_on_pages` opcional) e `keep_lines` (com `text` e `page`). O usuário revisou e aprovou os quatro arquivos.

`tests/unit/services/test_ingestion_running_lines.py` descobre os `*.running.yaml` e roda dois testes críticos, de tolerância zero, parametrizados por documento:
- cada `running_line` fica fora do texto dos chunks de cada página que não está em `keep_on_pages`;
- cada `keep_line` aparece no texto dos chunks da página anotada.

O teste junta os chunks de cada página antes de comparar, porque uma linha longa pode cair na divisa entre dois chunks. A comparação usa só letras e dígitos, sem diferença de caixa: o markdown escreve `**Inf. Inf.** , Londrina` e `Revista Foco |Curitiba (PR)|`, e o `normalize` de `answer_keys.py` mantém o `|`. A leitura do gabarito entra em `tests/fixtures/answer_keys.py`, junto com a dos outros gabaritos.

Os testes do cleaner (issue #20) usam páginas sintéticas e cobrem cada regra da detecção e a preservação do tamanho do texto. Um teste em `test_positioning.py` cobre a caixa marcada.

## Risks / Trade-offs

- [A árvore de seções muda quando os títulos falsos vindos de cabeçalhos somem, e o placar de identificação pode cair] → `test_ingestion_sections.py` e `test_retrieval_answer_keys.py` rodam como guarda antes e depois. Se algum cair, a implementação para e a decisão volta para o usuário.
  - Ocorreu na implementação: o placar caiu de 63/63 para 62/63. No recuperando, "REFERÊNCIAS" é a última linha da página 23 e só o rodapé vinha depois dela. Sem o rodapé, o primeiro chunk da seção cai na página 24, e a métrica lê a página pelo primeiro chunk. Nenhum texto se perdeu. O usuário decidiu baixar `MIN_SECTION_IDENTIFICATION_RATE` de 1.0 para 0.98, o placar medido arredondado para baixo.
- [O layout junta uma linha corrida com outro texto numa caixa só, e a chave dessa caixa não se repete] → Na página 1 do recuperando, o rodapé vem com a URL da revista e fica no texto. O usuário aceitou o caso, e o gabarito mantém o rodapé nessa página (`keep_on_pages: [1]`). A regra de detecção não compara prefixos de chave.
- [Os `chunk_id` mudam de índice nas páginas onde um chunk só tinha cabeçalho] → Os `chunk_id` vivem só dentro de uma avaliação, porque a ingestão roda de novo a cada uma.
- [Um documento com poucas páginas e cabeçalho marcado como `text` não chega a 3 repetições] → Fica no texto, como hoje. Um documento novo no acervo com esse caso pede um ajuste dos limiares em outra mudança.
- [Um parágrafo real que comece no topo de várias páginas com o mesmo texto seria apagado] → A regra pede o mesmo texto, com dígitos normalizados, em 30% das páginas. O acervo não tem esse caso.
- [As métricas de recuperação com IA podem mudar] → Uma tarefa roda `tests/ai/evaluation/retrieval` e registra o placar. Abaixo do piso, a implementação para e o usuário decide.
  - Ocorreu na implementação: contra `main`, o recall subiu de 69/129 para 71/129 e a precisão entre ramos de 40/202 para 42/199, e o acerto de seção e página caiu de 75/129 para 73/129. Os ramos `implicacoes-praticas-discutidas` e `justificativa-revisao`, da dengue, perderam blocos da seção anotada. O usuário aceitou a troca: `MIN_SECTION_PAGE_HIT_RATE` baixou de 0.58 para 0.56, o valor medido arredondado para baixo, e `MIN_EVIDENCE_RECALL` subiu para 0.55 e `MIN_BRANCH_PRECISION` para 0.21.

## Migration Plan

Sem migração. `process_release_pipeline` ingere o documento a cada avaliação, então cada documento recebe os chunks limpos na próxima avaliação. Para reverter, basta reverter o commit.
