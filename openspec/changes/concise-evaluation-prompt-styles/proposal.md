## Why

A gestão relatou que os textos gerados pela IA na auditoria de documentos são longos demais,
sugerem mais do que deveriam e chegam em blocos de texto corrido difíceis de ler quando há muito
a comentar. A causa está nos próprios prompts: `DOCUMENT_ANALYSIS_PROMPT` define como "o mais
importante" fornecer insights de melhoria e exige o parecer em "um único parágrafo", e a síntese
(`DESCRIPTION`) pede saudação, apresentação e "argumentos analíticos" em parágrafos por seção.

## What Changes

- **Prompts de avaliação e síntese reescritos para objetividade**: remoção da persona extensa,
  dos emojis e das instruções que incentivam texto longo; limites explícitos de tamanho (número
  de itens e de palavras); saída em Markdown com listas, sem parágrafos longos.
- **Política única de sugestões**: critério atendido não recebe sugestão; critério parcialmente
  atendido ou não atendido recebe no máximo uma ação curta por lacuna identificada.
- **Variação aleatória de estilo de resposta**: o prompt passa a ser composto por uma base fixa
  (regras, barema, citações, formato JSON) mais um bloco de estilo sorteado.
  - Parecer por critério: um estilo sorteado **por critério** entre quatro opções (Veredito +
    listas, Checklist, Tabela, Resumo + tópicos).
  - Síntese executiva: um estilo sorteado por síntese entre três opções compatíveis com as seções
    fixas, mantendo os títulos `# Pontos atendidos`, `# Pontos a aprimorar` e
    `# Orientação final`, com saudação reduzida a uma frase.
  - O estilo sorteado não é persistido nem registrado; a seleção futura por tipo de pergunta
    deverá substituir o sorteio sem alterar a composição base + estilo.
- **`verbosity="low"` nos estágios de avaliação e síntese**: aplicado apenas a esses dois
  estágios, sem alterar o modelo global usado pelo chat.
- **Descrições dos schemas ajustadas**: o campo `feedback` de `DocumentReleaseFeedback` deixa de
  pedir parecer "detalhado".

## Capabilities

### New Capabilities
<!-- Nenhuma capacidade nova. -->

### Modified Capabilities
- `ai-pipeline`: o parecer por critério e a síntese executiva passam a ter formato curto em
  Markdown, política restrita de sugestões e estilo de resposta variável.

## Impact

- **Código afetado**:
  - `lumina/prompts.py`: `DOCUMENT_ANALYSIS_PROMPT` e `DESCRIPTION` reescritos; novos blocos de
    estilo `EVALUATION_STYLES` e `SYNTHESIS_STYLES`.
  - `lumina/services/ai/stages/evaluation.py`: sorteio de estilo por critério e
    `verbosity="low"` na chain de avaliação.
  - `lumina/services/ai/stages/synthesis.py`: sorteio de estilo da síntese, formatação dos
    pareceres de entrada e `verbosity="low"`.
  - `lumina/schemas/document_release.py`: descrição do campo `feedback`.
- **Fora do escopo**: prompts do chat (`PROMPTS.CHAT`) e do assistente
  (`assistant_service.chat_with_document`), que terão uma mudança dedicada; prompts internos de
  saída estruturada (análise de seção, expansão de consulta, sugestão de árvore, ABNT, verificação
  visual); barema de 0 a 10 e regras de citação, que permanecem inalterados.
- **APIs**: nenhuma alteração de contrato. `feedback` e `DocumentRelease.description` continuam
  `str`, agora com conteúdo em Markdown.
- **Frontend (`lumina-front`)**: hoje exibe esses campos como texto puro ou por um renderizador
  linha a linha que não interpreta Markdown. A adequação fica a cargo da equipe de frontend, a
  partir da lista de mudanças em `design.md`; este repositório não altera o frontend.
- **Testes**: novos testes de composição de prompt e sorteio de estilo; os testes de
  `partition_synthesis_text` continuam válidos, pois os títulos das seções não mudam.
