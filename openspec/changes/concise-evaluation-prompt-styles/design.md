## Context

O pipeline de auditoria gera dois textos lidos diretamente pelo analista e pela gestão:

- **Parecer por critério**: `DOCUMENT_ANALYSIS_PROMPT` (`lumina/prompts.py`), executado em lote por
  `stages/evaluation.py` (`prompt | model | JsonOutputParser`), com saída
  `DocumentReleaseFeedback` (`feedback`, `fulfilled`, `score`, `citations`).
- **Síntese executiva**: `DESCRIPTION` (`lumina/prompts.py`), montada por
  `stages/synthesis.py` a partir dos 2 critérios de maior e dos 2 de menor nota, e particionada por
  `partition_synthesis_text` nos títulos `# Pontos atendidos`, `# Pontos a aprimorar` e
  `# Orientação final`.

Os dois prompts induzem verbosidade e sugestões. O parecer tem como "o mais importante" fornecer
insights e é pedido em "um único parágrafo"; a descrição do schema pede "parecer detalhado". A
síntese exige saudação, apresentação e parágrafos de "argumentos analíticos". Como os pareceres
longos alimentam a síntese, o efeito se acumula.

O modelo padrão é `gpt-5-mini` (`lumina/core/llm.py`), compartilhado com o chat.

## Goals / Non-Goals

**Goals:**
- Pareceres e síntese curtos, em Markdown estruturado, com limites explícitos de tamanho.
- Sugestões apenas para lacunas, no máximo uma ação por lacuna.
- Variação de estilo de resposta por sorteio, em uma estrutura que permita trocar o sorteio por
  seleção orientada (por tipo de pergunta ou outra variável) sem reescrever os prompts.
- Nenhuma alteração de contrato de API, de banco ou do barema de 0 a 10.

**Non-Goals:**
- Prompts do chat (`PROMPTS.CHAT`) e do assistente (`assistant_service`); terão mudança própria.
- Seleção de estilo por tipo de pergunta (fase futura).
- Persistência ou telemetria do estilo sorteado.
- Alterações no `lumina-front` (listadas ao final para a equipe responsável).

## Decisions

### 1. Composição "base fixa + bloco de estilo" em vez de prompts completos por estilo
- **Decisão**: `DOCUMENT_ANALYSIS_PROMPT` e `DESCRIPTION` mantêm as regras invariantes (barema,
  fidelidade aos trechos, citações, política de sugestões, limites de tamanho, formato JSON) e
  recebem um placeholder `{style_instructions}`. Os estilos ficam em dicionários
  `EVALUATION_STYLES` e `SYNTHESIS_STYLES` em `lumina/prompts.py`, chave = identificador do
  estilo, valor = instrução curta com um exemplo de formato.
- **Motivo**: evita que quatro prompts completos divirjam nas regras ao longo do tempo; a
  variação fica isolada no que muda de fato (a forma da resposta).
- *Alternativa considerada*: um prompt completo por estilo. Rejeitada pela duplicação das regras
  de citação e de barema.

### 2. Estilos disponíveis
- **Parecer por critério** (`EVALUATION_STYLES`):
  - `verdict_lists` (Veredito + listas): linha `**Situação:**`, seguida das listas
    `**Evidências**` e `**Lacunas**` (esta omitida quando não houver lacunas).
  - `checklist`: uma linha por aspecto verificado, marcada com ✅ (atende), ⚠️ (parcial) ou
    ❌ (não atende).
  - `table`: tabela `Aspecto | Situação | Observação`, com até 4 linhas.
  - `summary_bullets` (Resumo + tópicos): uma frase de veredito de até 25 palavras e até 3
    tópicos.
- **Síntese** (`SYNTHESIS_STYLES`): `bullets` (listas simples), `checklist` (marcadores ✅/⚠️ nas
  seções) e `summary_bullets` (uma frase de abertura por seção seguida de até 3 tópicos). A
  tabela não entra na síntese porque as seções já são fixas e curtas.
- Limites comuns: até 4 itens por lista; até 25 palavras por item no parecer; saudação da síntese
  em uma frase, sem autoapresentação.

### 3. Sorteio por critério, no início de `evaluate_criteria_batch`
- **Decisão**: antes do laço de retentativas, cada item de `eval_args` recebe
  `style_instructions` sorteado com `random.choice` sobre `EVALUATION_STYLES`. O
  `PromptTemplate` passa a declarar `style_instructions` em `input_variables`.
- **Motivo**: o sorteio fica junto do consumo, sem alterar `retrieval.py` nem `pipeline.py`.
  Sortear antes das retentativas mantém o mesmo estilo em caso de nova tentativa, e o
  `prompt_rendered` registrado pelo run logger reflete o prompt realmente enviado.
- A seleção fica em uma função (`select_evaluation_style`), que é o ponto de troca para a futura
  seleção orientada. Testes controlam o resultado com `monkeypatch` em `random.choice`.
- `save_applied_snapshot` lê apenas chaves específicas do payload, então a chave extra não afeta o
  snapshot.

### 4. Síntese com sorteio próprio e pareceres de entrada formatados em bloco
- **Decisão**: `generate_synthesis_prompt` sorteia um estilo de `SYNTHESIS_STYLES` por chamada. Os
  pareceres de entrada (agora em Markdown com várias linhas, possivelmente tabelas) deixam de ser
  interpolados em linha (`(Feedback: ...)`) e passam a ser apresentados como bloco indentado sob
  cada critério.
- **Motivo**: interpolar Markdown de várias linhas dentro de um item de lista confunde a leitura
  do modelo. Os títulos fixos das seções continuam literais no prompt-base, então
  `partition_synthesis_text` e o renderizador atual do frontend continuam reconhecendo as seções.

### 5. `verbosity="low"` via `model_copy`, só onde o modelo suportar
- **Decisão**: um helper aplica `model.model_copy(update={'verbosity': 'low'})` quando o modelo
  declara o campo `verbosity` (`ChatOpenAI` em `langchain-openai` 1.2.1); caso contrário, devolve
  o modelo inalterado. Usado em `get_evaluation_chain` e em `record_synthesis_stage`.
- **Motivo**: o modelo global é compartilhado com o chat, que está fora do escopo. `model_copy`
  preserva o tipo `ChatOpenAI` (e `model_name`, usado na decomposição da chain e no run logger),
  ao contrário de `bind`, que devolve um `RunnableBinding`. A verificação do campo mantém
  compatíveis os modelos falsos dos testes (`FakeListChatModel`).
- *Alternativa considerada*: `max_tokens` como teto rígido. Rejeitada porque truncaria o JSON da
  saída estruturada.

### 6. Linguagem dos prompts
- Instruções em segunda pessoa ao modelo, sem persona extensa, emojis decorativos ou texto
  dirigido ao analista dentro do prompt. As descrições de schema seguem a mesma linha
  (`feedback`: "Parecer curto em Markdown, no formato indicado").

## Risks / Trade-offs

- **[Risco] O frontend exibe Markdown cru até ser adequado**: asteriscos, `|` de tabela e `- `
  aparecem literalmente; linhas iniciadas por número viram títulos no renderizador da síntese.
  - *Mitigação*: os estilos evitam listas numeradas; a lista de adequações abaixo é entregue à
    equipe de frontend.
- **[Risco] Formatos variados dificultam comparação entre critérios de uma mesma release**:
  - *Mitigação*: aceito deliberadamente nesta fase para observar a preferência da gestão; a
    seleção orientada substituirá o sorteio.
- **[Risco] Modelo ignorar limites de tamanho**:
  - *Mitigação*: limites numéricos explícitos e `verbosity="low"`.
- **[Trade-off] Estilo sorteado não é registrado**: não será possível medir a preferência por
  estilo a partir dos dados; decisão consciente do solicitante.

## Mudanças necessárias no frontend (`lumina-front`)

A cargo da equipe de frontend; nada disso é implementado neste repositório.

1. **Parecer por critério** (`evaluation.feedback`): renderizar como Markdown com suporte a GFM
   (listas, negrito, tabelas) em `app/components/ResultadoAnaliseTipificacao.tsx` (hoje
   `<p className="whitespace-pre-wrap">`) e em `app/components/OiacIaChat.tsx` (hoje
   `<p className="whitespace-pre-wrap text-justify indent-6">`). Remover `text-justify` e
   `indent-6` nesse bloco, que deformam listas e tabelas.
2. **Síntese executiva** (`release.description`): em `ConteudoMensagem`
   (`OiacIaChat.tsx`), manter o destaque colorido dos títulos `Pontos atendidos`,
   `Pontos a aprimorar` e `Orientação final` (`tituloResumoAnalise`) e renderizar o conteúdo
   entre títulos como Markdown, em vez de um `<p>` por linha. Deixar de tratar linhas
   `^\d+\.\s` como título (`linhaTituloTopico`) dentro do conteúdo renderizado como Markdown.
   Também em `ResultadoAnaliseTipificacao.tsx`, onde `release.description` é exibido como texto
   puro.
3. **Tabelas**: garantir estilo e rolagem horizontal em telas estreitas (estilo `table` do
   parecer, até 3 colunas e 4 linhas).
4. **Emojis de situação** (✅ ⚠️ ❌): usados nos estilos `checklist`; conferir a renderização
   na fonte da interface.
5. **Segurança**: renderizar Markdown sem HTML bruto (por exemplo, `react-markdown` sem
   `rehype-raw`), já que o conteúdo vem do modelo.
