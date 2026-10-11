# Guia para o frontend: pareceres e síntese em Markdown

## Resumo

Os textos gerados pela IA na avaliação de documentos passaram a vir em **Markdown**. São dois
campos:

| Campo | O que é |
| :--- | :--- |
| `description` da release | Síntese executiva da avaliação |
| `check_tree[].taxonomies[].branches[].evaluation.feedback` | Parecer de cada critério avaliado |

O contrato da API **não mudou**: os nomes dos campos, os tipos (`string`), os endpoints e os
demais campos continuam iguais. O que mudou é o **conteúdo** dessas duas strings, que agora
precisa ser renderizado como Markdown. Exibidas como texto puro, os símbolos de marcação
(`**`, `- `, `|`, `#`) aparecem literalmente para o usuário.

## Endpoints e eventos afetados

Todos retornam `DocumentReleasePublic` (ou uma lista dele), e o efeito é o mesmo nos dois campos
acima.

| Método | Rota | Onde aparecem os campos |
| :--- | :--- | :--- |
| `GET` | `/doc/{doc_id}/release` | `releases[].description` e `releases[].check_tree[].taxonomies[].branches[].evaluation.feedback` |
| `POST` | `/doc/{doc_id}/release` | Mesmos campos, na release criada (logo após a criação ainda vêm vazios, porque o processamento é assíncrono) |
| `POST` | `/doc/{doc_id}/release/from-file` | Idem ao anterior |
| WebSocket | `/ws/{subscriber_id}`, evento `doc.release.update` | `payload` é um `DocumentReleasePublic`, com os mesmos campos |

Também expõe o parecer, apenas para administradores: `GET /processing-runs/{run_id}`
(telemetria do pipeline).

**Não foram alterados:** o chat com o documento (`POST /doc/{doc_id}/message/ai`) e o assistente
(`POST /doc/{doc_id}/assistant/chat`). As respostas deles continuam como antes.

## Onde esses campos aparecem hoje no `lumina-front`

Levantamento feito no código atual, para facilitar a localização:

| Arquivo | Campo | Exibição atual |
| :--- | :--- | :--- |
| `app/components/ResultadoAnaliseTipificacao.tsx` | `evaluation.feedback` | Texto puro (`whitespace-pre-wrap`) |
| `app/components/ResultadoAnaliseTipificacao.tsx` | `release.description` | Texto puro (`whitespace-pre-wrap`) |
| `app/components/OiacIaChat.tsx` | `evaluation.feedback` | Texto puro (`whitespace-pre-wrap`) |
| `app/components/OiacIaChat.tsx` (`ConteudoMensagem`) | `release.description` | Renderizador próprio, linha a linha: reconhece títulos `#` e os títulos da síntese, e exibe as demais linhas como parágrafos de texto puro |

## Markdown que precisa ser suportado

O conteúdo segue CommonMark com a extensão de tabelas do GitHub (GFM). Os elementos produzidos são:

| Elemento | Sintaxe | Onde aparece |
| :--- | :--- | :--- |
| Parágrafo | Texto separado por linha em branco | Pareceres e síntese |
| Negrito | `**texto**`, inclusive no meio da linha (`- **Atende:** prazo definido.`) | Pareceres e síntese |
| Lista não ordenada | Linhas iniciadas por `- ` | Pareceres e síntese |
| Tabela | GFM, com linha de cabeçalho e separador `\|---\|` | Somente pareceres |
| Título de nível 1 | `# Título` | Somente síntese (os três títulos fixos abaixo) |

Os textos não usam listas numeradas, emojis nem HTML. Como o conteúdo é gerado por um modelo de
linguagem, outros elementos básicos de Markdown podem aparecer ocasionalmente; um renderizador
CommonMark + GFM completo cobre esses casos.

### Segurança

O conteúdo é gerado por IA e deve ser tratado como não confiável: o renderizador **não deve
interpretar HTML bruto** contido no texto (por exemplo, `react-markdown` sem `rehype-raw`, ou
sanitização do HTML gerado).

## Estrutura da síntese (`description`)

A síntese mantém a mesma estrutura de seções de antes, com os **mesmos títulos, escritos
exatamente assim**:

```markdown
Uma frase de abertura com o resultado geral.

# Pontos atendidos
- ...

# Pontos a aprimorar
- ...

# Orientação final
- ...
```

- A frase de abertura vem antes do primeiro título (é o bloco que o front hoje trata como
  saudação/apresentação).
- O conteúdo de cada seção agora é uma lista (`- `), às vezes precedida de uma frase curta, e pode
  ter negrito no início dos itens.
- A identificação das seções pelos títulos, feita hoje em `tituloResumoAnalise`, continua válida.

## Formato dos pareceres (`feedback`)

Cada critério recebe o parecer em **um de quatro formatos**, escolhido aleatoriamente pelo backend
**por critério**. Uma mesma release mistura formatos, e não há campo indicando qual foi usado. O
front não deve depender de uma estrutura fixa nem tentar interpretar o conteúdo: basta renderizar o
Markdown. Exemplos reais de cada formato:

**1. Situação e listas**

```markdown
**Situação:** Atende parcialmente

**Evidências**
- Prazo de entrega de 30 dias definido.

**Lacunas**
- Modalidade de garantia ausente: indique as modalidades aceitas.
```

**2. Lista com rótulo de situação**

```markdown
- **Atende:** prazo de entrega de 30 dias definido.
- **Não atende:** modalidade de garantia ausente; indique as modalidades aceitas.
```

**3. Tabela**

```markdown
| Aspecto | Situação | Observação |
|---|---|---|
| Prazo de entrega | Atende | 30 dias definidos |
| Garantia | Não atende | Indique as modalidades aceitas |
```

**4. Frase de veredito e tópicos**

```markdown
Atende parcialmente: o prazo está definido, mas falta a modalidade de garantia.

- Prazo de entrega de 30 dias definido.
- Falta a modalidade de garantia: indique as modalidades aceitas.
```

## Compatibilidade

- **Releases antigas** (processadas antes desta mudança) continuam com o texto em parágrafos
  corridos. Texto puro também é Markdown válido, então o mesmo renderizador atende os dois casos.
- **Ordem de publicação:** o backend pode ir para produção antes do front. Até o front ser
  atualizado, as releases novas exibirão os símbolos de Markdown literalmente.

## Como ver respostas reais

Com o backend rodando, a página `/demos/evaluation_feedback/` permite enviar um PDF com uma
tipificação e ver a síntese e os pareceres reais, com o **Markdown bruto** de cada bloco (opção
"Ver Markdown bruto"). A opção "Ver exemplo sem API" mostra um parecer de cada formato sem
processar documento. A aparência dessa página serve só para conferir o conteúdo e não é referência
visual para o front.
