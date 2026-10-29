## Context

`anonymize_chunks` (`lumina/services/ai/stages/anonymization.py`) cria um `PresidioAnonymizer` por documento e passa todos os chunks de uma vez. O anonimizador analisa `page_content`, `section_title` e `section_path` de cada chunk em sequência e acumula o mapa de reversão em `existing_presidio_mapping`.

O `_setup_analyzer` carrega o modelo spaCy `pt_core_news_lg`, remove todos os reconhecedores do registro, inclusive o `SpacyRecognizer`, e registra 12 `PatternRecognizer`. Nenhum deles emite `PERSON`.

Medições feitas no acervo de `tests/fixtures/documents/` durante a exploração:

- Com o `SpacyRecognizer` de volta, "O texto foi escrito por Maria Souza" sai com `PERSON`. "ALANA CAROLINA PEREIRA ABREU" não: o modelo marca o trecho como `ORG` ou `MISC`. A mesma linha em caixa de título sai como `PER`.
- No `chunk_0_0` do anteprojeto, o chunk inteiro não está em maiúsculas: o prefixo e o título do trabalho vêm em caixa mista. A normalização precisa atuar em cada sequência de palavras em maiúsculas.
- O spaCy marca como `PER` expressões que não são nomes: "Dengue" (18 vezes), "Energias Renováveis", "Solar", "LLMs", "Q1", células de tabela. Os spans trazem resíduo de Markdown (`**`, `</mark><sup>1</sup`, quebra de linha seguida da próxima linha).
- Os quatro PDFs do acervo têm seção com papel `references`.

## Goals / Non-Goals

**Goals:**

- Mascarar os nomes de autoria do acervo (capa, folha de rosto, cabeçalho de artigo) em qualquer caixa e em todas as seções.
- Manter os trechos dos gabaritos de recuperação no texto anonimizado.

**Non-Goals:**

- Corrigir a árvore de seções que usa o nome da capa como título. O título passa a sair mascarado, e a correção da árvore fica na #42.
- Reconhecer nomes de uma palavra só. Um nome isolado no corpo ("Maria disse") continua visível.
- Trocar o modelo spaCy ou adicionar dicionário externo de nomes.

## Decisions

### 1. Duas passadas por documento dentro de `anonymize_chunks`

`PresidioAnonymizer.anonymize_chunks` coleta os nomes de todos os chunks antes de mascarar o primeiro. A coleta usa o pipeline spaCy do próprio `AnalyzerEngine` (`analyzer.nlp_engine`), sem carregar outro modelo. O mascaramento usa um `PatternRecognizer` de entidade `PERSON`, criado para o documento e registrado no analisador só durante a chamada.

Alternativa descartada: registrar o `SpacyRecognizer` e deixar o Presidio decidir chunk a chunk. Um nome marcado como `PER` num chunk e como `ORG` no título da seção vazaria no título, e cada falso positivo do modelo viraria máscara sem filtro.

### 2. Normalização de caixa por sequência em maiúsculas

Antes da coleta, cada sequência de duas ou mais palavras em maiúsculas passa para caixa de título (`str.title()`). O texto normalizado só alimenta a coleta: os nomes coletados voltam ao texto original pelo mascaramento sem distinção de caixa, então os offsets do texto normalizado não importam.

### 3. Filtro de candidatos

Um span `PER` vira nome do documento quando passa por todas as regras:

1. O span é cortado no primeiro caractere que não é letra, espaço, hífen, apóstrofo ou ponto, e na primeira quebra de linha. Isso remove o resíduo de Markdown e de HTML.
2. Sobram duas ou mais palavras, todas capitalizadas, exceto os conectivos `de`, `da`, `do`, `das`, `dos` e `e`.
3. Pelo menos uma palavra, fora os conectivos, não aparece em minúsculas no texto do documento. "Energias Renováveis" sai porque o documento escreve "energias" e "renováveis".
4. O candidato não é igual, sem distinção de caixa e sem a numeração, ao título de uma seção do documento. "Aplicações Correlatadas" sai porque é o título "3 APLICAÇÕES CORRELATADAS".

Coleta medida no acervo com as regras 1 a 3:

| Documento | Mantidos | Descartados pela regra 3 |
| :--- | :--- | :--- |
| anteprojeto | Alana Carolina Pereira Abreu, Eduardo Manuel de Freitas Jorge | nenhum |
| artigo renováveis | 5 autores, Coelho Júnior, Gonzalez e Lima, Stela Experta, Aplicações Correlatadas | Energia Limpa, Energia Solar, Energias Renováveis |
| dengue | 8 autores, Dr. Renato Figueiredo Varella, Benjamin Rush, Siqueira Jr, Glaxo Smith Kline, Rua Prof | Agente Etiológico, Vetor da Doença |
| microgrids | 5 autores, Paulo de Tarso, Nascimento Filho, Regarding ANN | nenhum |

Nenhum candidato mantido aparece num trecho de `*.retrieval.yaml`.

### 4. Seção de referências fora da coleta

A coleta ignora chunks com `section_role == references`. O mascaramento roda em todos os chunks. Assim a autora que se cita some também na referência, e "FERREIRA, Bruno Carlos Luís", que só aparece em References, continua no texto e no gabarito.

### 5. Casamento sem distinção de caixa

O reconhecedor do documento usa uma única expressão regular com os nomes em alternância, do mais longo para o mais curto, com `re.IGNORECASE`, limites de palavra e `\s+` entre as palavras. A ordem faz "Rosemeire Terezinha Da Silva" vencer "Rosemeire Terezinha" na mesma posição. O `\s+` cobre nomes quebrados em duas linhas.

### 6. Um marcador por nome, em qualquer caixa

`InstanceCounterAnonymizer` procura o texto no mapa sem distinção de caixa antes de criar um índice novo. Quando acha, devolve o marcador existente e não grava a nova forma. O mapa guarda uma forma por marcador, a primeira que apareceu.

Alternativa descartada: gravar todas as formas apontando para o mesmo marcador. O `PresidioDeanonymizer` percorre o mapa e cria uma entidade por par; com duas formas para `<PERSON_0>`, criaria duas entidades sobrepostas no mesmo trecho.

A regra vale para todas as entidades, não só `PERSON`. Para CPF, e-mail e afins a caixa não muda o dado.

## Testes

A jornada é a do proponente que envia o anteprojeto: o texto que chega ao provedor externo não pode trazer o nome dele. O teste de jornada passa pela interface do estágio (`anonymize_chunks` sobre os chunks de `extract_pdf_chunks`), a mesma que `run_document_ingestion` usa. Subir a rota de upload exigiria mock de embeddings e de armazenamento sem provar nada a mais sobre a anonimização.

- **Crítico, tolerância zero, sobre o acervo:** cada `<nome>.sections.yaml` ganha a lista `person_names` com os nomes de autoria do documento. O teste falha se algum nome da lista, normalizado, aparecer em `page_content`, `section_title` ou `section_path` de um chunk anonimizado, e aponta documento, chunk e campo.
- **Focados, em `test_metadata_anonymization.py`, com textos curtos:** nome em maiúsculas; mesmo nome em duas caixas com um só marcador e uma só forma no mapa; nome da autoria em References; autor só de References visível; sobrenome de citação visível; expressão descartada pela regra 3; expressão igual a título de seção.
- **Guardas:** `test_retrieval_answer_keys.py` e `test_ingestion_sections.py` continuam passando sem mudar os gabaritos de trechos.

## Risks / Trade-offs

- [Autor citado com duas palavras no corpo ("Gonzalez e Lima", "Benjamin Rush") é mascarado] → Aceito. Conta como nome de pessoa do documento, e a avaliação dos critérios não depende do nome do autor citado.
- [Falso positivo que passa no filtro ("Glaxo Smith Kline", "Rua Prof", "Regarding ANN") vira máscara em todo o documento] → Os testes focados fixam as regras. O placar de recuperação com IA, medido de novo, mostra se a perda afeta a busca.
- [Nome partido entre dois chunks] → O spaCy não vê o nome inteiro no chunk que o corta. A coleta roda sobre todo o documento, e o nome inteiro costuma aparecer em outro lugar (capa, cabeçalho). A parte cortada fica visível.
- [Ingestão mais lenta] → A coleta roda o pipeline spaCy uma vez por chunk, além da análise do Presidio. A tarefa de verificação mede o tempo de `test_ingestion_sections.py` antes e depois.
- [`presidio_mapping` já gravado no banco] → Documentos ingeridos antes da mudança mantêm o mapa antigo, sem `PERSON`. A reversão continua funcionando para eles. Reprocessar o acervo de produção fica fora desta change.
