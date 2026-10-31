# Proposal

## Why

Usuários reclamam que a IA "marcou a seção inteira" quando devia sinalizar um parágrafo. A menor unidade que o modelo consegue citar é o chunk, com até 1000 caracteres, e o sistema destaca todas as linhas dele: 7 a 10 linhas na mediana do acervo anotado, com mais de um parágrafo em 62% a 78% dos chunks. Em 305 frases do acervo, o destaque por frase cobriu 25% a 41% das linhas do chunk na mediana.

## What Changes

- A ingestão divide o texto de cada chunk em frases numeradas, com a posição no texto anonimizado e retângulos próprios no PDF.
- O contexto enviado à avaliação e ao chat marca cada frase com `[s1]`, `[s2]` e assim por diante.
- O modelo cita o `chunk_id` e os números das frases. Cada citação vira uma referência, com os retângulos só dessas frases e o texto delas em `text_snippet`.
- O sistema aceita mais de uma citação por chunk. Hoje ele descarta a segunda.
- Chunks sem frases numeradas, como os de documentos já indexados, e citações sem frase válida continuam com os retângulos do chunk inteiro.
- O formato de `DocumentReference` não muda, então o frontend continua funcionando sem alteração nos critérios.

Documentos antigos não serão reindexados. As referências já salvas ficam como estão. Toda nova avaliação refaz a ingestão do arquivo e recebe as frases numeradas.

Fora desta mudança:

- Exibir no frontend as evidências das respostas do chat. O front ignora `references` em `/doc/{id}/message/ai`, e isso fica para uma issue (ver Impact).
- Ligar cada item do parecer a um destaque e indicar onde corrigir uma lacuna sem trecho no documento.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `ai-pipeline`: acrescenta as frases citáveis por chunk, a citação por frase na avaliação e no chat, a proteção de dados pessoais nas frases e o critério de aceite sobre o acervo anotado.

## Impact

- **Ingestão:** `lumina/services/ai/stages/extraction.py`, `positioning.py`, `lumina/services/ai/pipeline.py`, novo módulo de frases em `stages/` e `lumina/utils/PresidioAnonymizer.py`.
- **Contexto e citações:** `stages/retrieval.py`, `stages/citations.py`, `lumina/schemas/ai.py`, `lumina/schemas/document_release.py` e `lumina/prompts.py`.
- **Dados:** o metadado JSONB dos chunks novos ganha o campo `sentences`. Os retângulos ocuparam 1,5 a 2,8 vezes mais espaço no protótipo, de 4 a 29 KB para 6 a 80 KB por documento. Não há migração.
- **Custo:** os marcadores acrescentam tokens a cada avaliação. O protótipo gerou 9 a 23 marcadores por 1000 caracteres antes de juntar fragmentos curtos.
- **Testes:** novos testes sobre o acervo de `tests/fixtures/documents/` e nova avaliação com IA em `tests/ai/evaluation/`.
- **Documentação:** `docs/ia-plataforma.md`.
- **Issue a abrir:** exibir as evidências do chat no `lumina-front`, com o modelo `.github/ISSUE_TEMPLATE/demanda.md`.
