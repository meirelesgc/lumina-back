# Design

## Context

A motivação está em `proposal.md`. Quatro fatos do código moldam a solução:

- `resolve_citations` copia `metadata['rects']` do chunk e ignora `text_snippet` na posição. O `seen` guarda só o `chunk_id` e descarta a segunda citação do mesmo chunk.
- `locate_range` já aceita qualquer intervalo de caracteres do Markdown. No protótipo, ele localizou 305 de 305 frases exatas.
- `extract_pdf_chunks` fecha o PDF ao terminar, e os `rects` precisam do PDF aberto. Por isso as frases nascem na ingestão, e o texto anonimizado só existe depois dela.
- `process_release_pipeline` chama `run_document_ingestion` a cada avaliação. Uma nova avaliação sempre recebe chunks novos. Só o chat lê chunks antigos do vector store.

O texto vai ao modelo por `format_context` (avaliação) e `build_chunk_prompts` (chat).

Protótipo sobre os 4 PDFs do acervo, sem juntar fragmentos: mediana de 3 a 6 frases por chunk e 1% a 16% das frases sem retângulo. Em `smart_tech_microgrids`, a mediana caiu para 12 caracteres por frase por causa de linhas de tabela, o que justifica a junção de fragmentos curtos.

## Goals / Non-Goals

**Goals:**

- Destacar só as frases que fundamentam a citação, na avaliação e nas respostas do chat.
- Manter o formato de `DocumentReference`, para o frontend funcionar sem alteração nos critérios.
- Manter a busca, os embeddings e o `chunk_id` como estão.

**Non-Goals:**

- Reindexar documentos ou reescrever referências salvas.
- Mudar o tamanho dos chunks.
- Alterar o frontend ou ligar os itens do parecer aos destaques.

## Decisions

### 1. A frase é a unidade citável

Uma citação com várias frases vizinhas cobre um parágrafo, então a frase atende os dois casos. Citar parágrafos deixaria de fora quem precisa de uma frase só.

### 2. Número local dentro do chunk

O texto vai como `[s1] ... [s2] ...`, e a citação vira `{"chunk_id": "chunk_3_1", "sentences": [1, 2]}`. O `chunk_id` continua idêntico. Citações de um trecho contínuo saem como uma referência, sem precisar de fusão posterior.

Alternativa descartada: ID global por frase, como `chunk_3_1.s2`. Ele custa mais tokens e cria uma referência por frase, que a tela mostraria como vários botões iguais.

### 3. Trecho literal fica fora da solução

`Citation.text_snippet` continua opcional no schema, mas não define posição. O modelo escolhe entre números existentes, então não há alinhamento aproximado com paráfrases nem com `<PERSON_n>`. O backend preenche `text_snippet` da referência com o texto das frases.

### 4. Segmentação determinística com regex

Um módulo novo em `stages/sentences.py` divide o corpo do chunk em fim de frase seguido de maiúscula, número ou marcador, em linha em branco e em início de item de lista ou tabela. Uma lista de abreviações impede cortes em casos como `et al.`, `Art.`, `Dr.`, `p.` e `Fig.`. Fragmentos com menos de 40 caracteres se juntam à frase seguinte.

O limite de 40 ficou confirmado: a mediana das frases subiu de 12 a 112 caracteres para 85 a 152, e os marcadores caíram para 6,1 a 8,5 por 1000 caracteres.

Alternativa descartada: spaCy. Ele acrescenta processamento por chunk, e a segmentação ficaria presa à versão do modelo. O acervo tem documentos em português e em inglês. Os testes do acervo medem o resultado da regex.

### 5. Metadado guarda posição, sem texto

O chunk ganha:

```json
"sentences": [
  {"n": 1, "start": 12, "end": 88, "rects": [[50.0, 100.0, 500.0, 115.0]]}
]
```

`start` e `end` apontam para `page_content`. O texto da frase sai do fatiamento de `page_content` na hora de montar o prompt. Sem cópia do texto, o metadado não abre um novo caminho para dado pessoal.

### 6. Fluxo em duas fases

Na extração, depois de `run_chunk_pipeline`, o sistema segmenta o corpo limpo. Ele mapeia cada frase para o Markdown comparando os tokens com `tokenize_with_offsets`, porque `clean_whitespace` altera deslocamentos. Em seguida chama `locate_range` com o PDF ainda aberto.

Na anonimização, `_anonymize_text` devolve as posições de cada entidade no texto original e no final. `EngineResult.items` informa só as posições finais, e os conflitos entre entidades mudam o que o `analyzer` encontrou, então `InstanceCounterAnonymizer` registra o tamanho original de cada entidade. `_anonymize_each_chunk` recalcula `start` e `end` com esse mapeamento. Uma fronteira dentro de uma entidade passa para o fim do marcador.

Alternativa descartada: anonimizar cada frase isolada. Isso multiplica as chamadas ao NER e tira o contexto que o reconhecimento de nomes usa.

Alternativa descartada: marcadores invisíveis no texto durante a anonimização. O mapeamento por posições não altera o texto que o NER recebe.

### 7. Compatibilidade pela ausência do campo

Um helper único renderiza o corpo do chunk para os dois prompts e devolve o texto sem marcadores quando `sentences` falta. `resolve_citations` usa os `rects` do chunk nos casos sem frase válida. A chave de deduplicação passa a ser `(chunk_id, frases)`, com as frases ordenadas e sem repetição.

### 8. Testes

Jornada: um analista envia um PDF e clica em uma evidência; a resposta traz destaque só na frase citada, em vez do chunk todo. O teste estende `tests/integration/test_release_pipeline.py`, que percorre o pipeline com modelo substituído por uma resposta fixa. A interface pública da API não expõe as etapas internas, e a citação fixa do modelo é o que torna o resultado determinístico.

Regras de segmentação, mapeamento de anonimização e resolução de citações ficam em testes unitários. O acervo segue as duas classes de `references/05-ia.md`: cobertura do texto com tolerância zero e qualidade com piso. A precisão do modelo real fica em `tests/ai/evaluation/citations/`, marcada com `ai`, sem piso nesta mudança.

## Risks / Trade-offs

- [O modelo omite `sentences` e cita só o chunk] → O sistema cai no comportamento atual. O prompt exige os números e a avaliação com IA mede a taxa de citações por frase.
- [Mais tokens por avaliação] → A junção de fragmentos reduz os marcadores para 6,1 a 8,5 por 1000 caracteres. Com cerca de 3 tokens por marcador e 4 caracteres por token, o acréscimo estimado fica entre 7% e 10%. Esse número é uma estimativa, sem medição de consumo antes e depois.
- [Frases sem retângulo: 4,1% no acervo, 68 de 1652] → As amostras inspecionadas são cabeçalhos e rodapés corridos, como `Energies 2025, 18, 2676 2 of 20`, que caem em blocos ignorados. A referência cai nos retângulos do chunk, e o piso de 0,95 impede regressão.
- [Regex corta frase em abreviação desconhecida] → O dano é um destaque menor que o ideal. O texto não se perde, porque a cobertura tem tolerância zero.
- [Modelo cita a frase errada] → A posição fica precisa, mas o usuário vê um erro mais fino. A avaliação com IA compara as frases com os trechos anotados.
- [Tooltip com `<PERSON_n>`] → `text_snippet` já podia trazer marcadores. Reverter a anonimização nele fica fora desta mudança.

## Migration Plan

Não há migração de banco nem reindexação. O campo `sentences` é aditivo no JSONB. Reverter o código devolve o comportamento anterior, e o campo fica ignorado nos chunks já gravados.

## Resultados medidos

Pisos do acervo em `test_sentences_corpus.py`: fração de frases com retângulos de 0,95 (medida: 0,959) e mediana de linhas da frase em relação ao chunk de até 0,3 (medida por documento: 0,22 a 0,29).

Avaliação com o modelo real sobre os 3 PDFs com gabarito de recuperação, em `tests/ai/evaluation/citations/test_citation_precision.py`:

- O modelo citou frases em 245 de 248 citações.
- As referências destacaram 1513 linhas, contra 2287 linhas dos chunks citados (66%). A conta soma o chunk uma vez por referência e pode contar a mesma linha em duas frases, então serve como ordem de grandeza.
- 97 de 129 trechos anotados (75%) apareceram nas frases citadas. A comparação exige que um texto contenha o outro, então paráfrases e citações parciais de outro ponto do trecho contam como erro.

Esta mudança não registra piso para essas métricas. O ganho real por citação fica abaixo do ganho por frase isolada, porque o modelo costuma citar várias frases.
