## Context

Os modelos ficam configurados em três lugares:

| Onde | Hoje | Como chama |
| :--- | :--- | :--- |
| `lumina/core/llm.py`, modelo principal (`get_model`) | `gpt-5-mini`, `temperature = 0.1` | `ChatOpenAI` |
| `lumina/core/llm.py`, modelo rápido (`get_fast_model`) | `gpt-4o-mini`, `temperature = 0` | `ChatOpenAI` |
| `lumina/features/template_check/constants.py` | `gpt-5.4-mini`, `effort = none`, `temperature = 0`, imagens | `AsyncOpenAI().responses.parse` |
| `lumina/features/abnt_check/abnt.py` | `gpt-5.4`, `effort = none`, `temperature = 0`, PDF como arquivo | `OpenAI().responses.parse` |

Testes feitos no planejamento, com chamadas mínimas na conta do projeto:

| Modelo | `effort` | `temperature` | Resultado |
| :--- | :--- | :--- | :--- |
| `gpt-6-luna` | `none` | `0` | Aceita |
| `gpt-6.1-sol` | `medium` | `0.1` | Erro 400: `temperature` não suportado |
| `gpt-6.1-sol` | `medium` | ausente | Aceita |
| `gpt-6-luna` com imagem | `none` | `0` | Leu a imagem |
| `gpt-6.1-sol` com PDF (`input_file`) | `medium` | ausente | Leu o PDF |

Com `reasoning` configurado, o `ChatOpenAI` usa a Responses API e devolve `AIMessage.content` como lista de blocos (`[{'type': 'text', 'text': ...}]`). Quatro pontos leem `content` como texto:

- `evaluation._extract_raw_text` faz `str(raw_resp.content)`. O parser falha, e `_process_eval_item` grava `fulfilled = False` com "Erro na validação de schema".
- `synthesis.generate_release_synthesis` faz `content.strip()`, o que quebra numa lista.
- `chat.py` e `assistant_service.py` devolvem `response.content` ao frontend.

`AIMessage.text` (langchain-core 1.3.2) devolve o texto nos dois formatos. A verificação foi feita no planejamento. `JsonOutputParser` já lê blocos corretamente quando recebe a mensagem.

## Goals / Non-Goals

**Goals:**
- Os dois usos (rápido e médio) com nome e parâmetros num único lugar.
- Todas as leituras de resposta funcionando com blocos e com texto simples.

**Non-Goals:**
- Mudar prompts, fluxo do chat ou recuperação.
- Ajustar os prompts ao comportamento dos modelos novos. Se os pareceres mudarem de tom, isso fica para depois da linha de base da #26.

## Decisions

### Configuração única por uso

`lumina/core/llm.py` define constantes por uso: `FAST_MODEL`, `FAST_REASONING_EFFORT`, `FAST_TEMPERATURE`, `MAIN_MODEL` e `MAIN_REASONING_EFFORT`. `ChatOpenAI` recebe `reasoning={'effort': ...}`, o mesmo formato que os módulos de visão já usam. O modelo principal não recebe `temperature`. `get_fast_model` mantém a assinatura, porque os chamadores não passam argumentos.

`template_check/constants.py` passa a usar o uso rápido, e `abnt_check/abnt.py` o uso médio, importando as constantes de `lumina/core/llm.py`. O `abnt_check` deixa de passar `temperature`. Os comentários desses arquivos que explicam a combinação de `temperature` com `effort` são atualizados.

Alternativa: settings por variável de ambiente. Rejeitada por enquanto: ninguém pediu trocar modelo sem deploy, e os parâmetros dependem do modelo (`temperature` vale para um e quebra o outro).

### Texto da resposta por `AIMessage.text`

Os quatro pontos passam a ler `.text`. Em `_extract_raw_text`, objetos sem `.text` continuam convertidos com `str`, como hoje.

Alternativa: `output_version` no `ChatOpenAI` para forçar texto simples. Rejeitada porque depende de detalhe interno do LangChain e não protege contra outro modelo que devolva blocos.

### `with_low_verbosity`

A função copia o modelo com `verbosity = 'low'` quando o `ChatOpenAI` tem o campo, e ele tem. O teste com IA confirma que o `gpt-6.1-sol` aceita o parâmetro. Se recusar, a função deixa de aplicar `verbosity` a esse modelo, e o motivo fica registrado em `tasks.md`.

### Testes

Jornada: o analista envia um documento, recebe os pareceres de cada critério e a síntese, e conversa com o documento no chat. A troca de modelo não pode transformar pareceres válidos em "não contempla" nem mostrar estrutura de blocos na tela.

- Unitários, sem IA: a avaliação com `AIMessage` em blocos registra o veredito do JSON (falha hoje com erro de schema), a síntese grava só o texto e o chat e o assistente devolvem `str`.
- Com IA, em `tests/ai/evaluation/models/test_models_smoke.py` e `@pytest.mark.ai`: o modelo principal responde texto e saída estruturada (`with_structured_output`) e passa pela cadeia de avaliação com `verbosity`; o modelo rápido responde saída estruturada; a configuração de visão do rápido lê uma imagem; e a do médio lê um PDF por `input_file`. As entradas de imagem e PDF são geradas no teste, com uma página.

## Risks / Trade-offs

- [O `abnt_check` perde o determinismo de `effort = none` com `temperature = 0`] → Decisão do usuário: seguir a tabela de usos. O efeito fica registrado na proposta. Se a variação incomodar, o `abnt_check` volta para o uso rápido.
- [`effort = medium` aumenta latência e custo da avaliação, que dispara uma chamada por ramo] → A #26 mede tokens e tempo por release. O agrupamento de chamadas fica para ela.
- [Os pareceres mudam de estilo com o modelo novo] → Fora do escopo. A linha de base dos veredictos da #26 é medida depois desta troca.

## Migration Plan

Sem migração de dados. Pareceres antigos continuam como foram gerados. Para reverter, basta reverter o commit.
