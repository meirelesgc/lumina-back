## Context

`retrieve_criteria_payload` (`lumina/services/ai/stages/retrieval.py`) formata `PROMPTS.QUERY` com o título da taxonomia e o texto do ramo, e aplica o mesmo modelo a cada expansão. A busca léxica já recebe só `<título do ramo>: <descrição do ramo>`. Os chunks levam o prefixo `[título real da seção] ` no conteúdo, então o título da taxonomia nunca casa com o texto indexado.

O escopo do ramo vem de `branch_section_requirements`, gerado em segundo plano por `branch_analyzer.py` quando o ramo é criado ou editado. As expansões vêm de `branch_query_expansions`, geradas por `query_expansion_service.py`. Os dois prompts citam editais. Na recuperação, só `SPECIFIC_SECTION` muda a busca; `ENTIRE_DOCUMENT` cai no mesmo caminho de `UNKNOWN` sem que nada diga que esse é o comportamento esperado.

O teste de linha de base da recuperação (`measure-retrieval-on-annotated-corpus`) existe no working tree do mantenedor, sem commit. O gabarito dele congela expansões e escopo, então ele mede a mudança da consulta (#15), não a dos prompts (#17).

## Goals / Non-Goals

**Goals:**
- Consulta vetorial sem título de taxonomia, com o mesmo texto da busca léxica.
- Prompts de escopo e de expansão escritos para os documentos acadêmicos atendidos.
- `ENTIRE_DOCUMENT` com efeito descrito na spec e coberto por teste.

**Non-Goals:**
- Mudar o prompt de avaliação. Ele ainda recebe a taxonomia como "Tópico de referência" e a pergunta "Analise o item na seção <taxonomia>". O avaliador lê os trechos e não sofre o problema do embedding.
- Ampliar a evidência dos ramos `ENTIRE_DOCUMENT` (issue #19) ou filtrar por papel de seção (issue #18).
- Trocar a busca léxica AND por OR (issue #16).
- Regenerar automaticamente as análises e expansões já gravadas.

## Decisions

### Consulta = texto do ramo

A consulta passa a ser `<título>: <descrição>`, o mesmo `query_text` da busca léxica, com o tratamento de vazio que `requirement` já usa no payload. O modelo `PROMPTS.QUERY` sai de `prompts.py` porque fica sem uso.

Alternativas consideradas, com o mantenedor:
- Incluir a descrição da taxonomia. Traz contexto, mas dilui o embedding com texto que também não aparece no documento.
- Gerar um trecho hipotético por LLM (HyDE) antes da busca. Exige uma geração nova por ramo, persistida ou feita na avaliação. A forma de trecho afirmativo entra pelas expansões (decisão abaixo), sem custo novo.

### Forma de trecho esperado via expansões

O prompt de expansão passa a pedir formulações afirmativas, no estilo do texto do documento ("A revisão justifica-se pela ausência de estudos que..."), sem "o manuscrito apresenta". Os tipos `paraphrase`, `sub_question` e `section_hint` continuam, para não mudar o schema nem os dados gravados. A busca já funde as expansões com a consulta do ramo por RRF, então a consulta em forma de pergunta e as formulações em forma de trecho convivem.

### Prompt de escopo com exemplos acadêmicos

O prompt troca "editais e instrumentos convocatórios" por "documentos acadêmicos e técnicos (artigos, revisões sistemáticas, anteprojetos, relatórios técnicos)" e lista as seções típicas de cada um desses tipos. `SPECIFIC_SECTION` vale só quando uma única seção do tipo informado na tipificação concentra o conteúdo, e `expected_section` recebe o título dessa seção como está na lista. `ENTIRE_DOCUMENT` ganha exemplos acadêmicos (clareza da redação, coerência entre objetivos e conclusões, padronização de citações) e passa a cobrir o conteúdo que pode aparecer em mais de uma seção, como revisão da literatura e lacunas. O schema `BranchSectionRequirement` não muda.

A lista por tipo e a regra "na dúvida, documento inteiro" vieram da primeira medição do classificador (registro em `tasks.md`). Sem a lista, o modelo sugeria seções que o tipo de documento não tem, como "Discussão" em anteprojeto. Sem a regra, ele escolhia `SPECIFIC_SECTION` para todos os ramos. Com seção esperada, a busca fica restrita a ela, então uma seção errada esconde a evidência, e a busca global só perde precisão.

### `ENTIRE_DOCUMENT` = busca global, explícita

O código de `retrieve_criteria_payload` já busca no documento inteiro quando o escopo não é `SPECIFIC_SECTION`. A mudança registra esse efeito na spec e acrescenta um teste que falharia se alguém passasse a rotear `ENTIRE_DOCUMENT`. O teste protege um comportamento que já funciona e passa desde o início.

Alternativas consideradas, com o mantenedor: remover o valor (mexe em schema, dados e testes sem ganho na busca) ou dar mais trechos a esses ramos (sobrepõe a issue #19).

### Testes

Não há jornada de usuário nova: o analista continua pedindo a avaliação e lendo o parecer. Os testes ficam na camada unitária, onde a consulta montada e o pedido enviado ao modelo são observáveis com um vector store e um LLM falsos, já usados em `test_ai_stages.py`, `test_branch_analyzer.py` e `test_query_expansion_service.py`.

A qualidade da recuperação é medida com o teste de linha de base do working tree, rodado com `--run-ai` antes e depois da mudança da consulta. A qualidade da classificação é observada rodando o classificador novo e o antigo sobre os ramos do gabarito do anteprojeto e registrando as saídas em `tasks.md` para o mantenedor julgar. Esta mudança não cria gabarito de escopo: gabaritos do acervo são escritos pelo mantenedor.

## Risks / Trade-offs

- [Ramos curtos perdem contexto sem o título da taxonomia, por exemplo "Clareza" sob "Metodologia"] → as expansões e a descrição do ramo seguem na busca; a medição antes e depois mostra se algum ramo do acervo piorou.
- [Expansões e análises antigas, geradas com os prompts de edital, continuam ativas] → o mantenedor roda `poetry run task enrich-branches --force` depois do merge. As versões novas entram com `generation_version` maior e as avaliações antigas mantêm a versão registrada.
- [O classificador novo devolve títulos de seção que existem no documento, como "Problema de Pesquisa", em vez de nomes inventados, como "Contextualização do Problema". Antes, esses nomes raramente passavam do limiar de 0,25 do roteamento e a busca caía no documento inteiro. Agora o roteamento pode restringir a busca a uma seção errada] → a regra "na dúvida, documento inteiro" reduz o risco. O teste de linha de base congela o escopo do gabarito e não mede esse efeito; a medição com o escopo gerado pelo classificador fica para uma issue.
- [Acervo de medição com um único documento anotado] → o resultado indica tendência, não prova melhora geral. A recomendação de anotar mais documentos fica no README do acervo, na outra change.

## Migration Plan

1. Merge do PR.
2. Regenerar análises de escopo e expansões: `poetry run task enrich-branches --force` (aceita `--dry-run` e `--limit` para conferir antes).
3. Rollback: reverter o commit de código e rodar o mesmo comando para voltar às gerações com os prompts antigos.
