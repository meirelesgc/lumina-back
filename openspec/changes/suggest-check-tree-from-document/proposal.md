## Why

Hoje a árvore de verificação (`Source` → `Typification` → `Taxonomy` → `Branch`) é montada à mão, item a item, pelos CRUDs. Quando uma instituição tem um documento normativo próprio (ex.: o regulamento de trabalhos acadêmicos de uma universidade), transcrever as regras dele para a árvore é lento, sujeito a omissões e difícil de manter sincronizado. Queremos que o motor leia o documento e **proponha** a estrutura, mas sem tocar na árvore real até que uma pessoa valide cada item, seguindo um fluxo de dry-run com revisão humana.

## What Changes

- Novo fluxo de **sessão de sugestão**: o usuário envia um PDF normativo e, opcionalmente, uma tipificação existente para enriquecer. O sistema cria a sessão, processa o documento de forma assíncrona e expõe o status (`processing`, `ready`, `failed`, `completed`).
- Dois modos de geração:
  - **Criar do zero**: identifica os tipos documentais regulados e propõe uma ou mais `Typification`, cada uma com suas `Taxonomy` e `Branch`.
  - **Enriquecer**: para uma `Typification` existente, propõe novas taxonomias e ramos, **sugere alterações** de título/descrição em taxonomias e ramos existentes e sinaliza possíveis duplicatas. Nunca propõe remoções.
- O próprio documento enviado é proposto como um novo `Source` revisável. Quando é confirmado, passa a ser vinculado aos itens confirmados da sessão.
- Cada item sugerido traz **evidência**: trecho literal do documento, página(s) e justificativa. Sugestões cuja evidência não é encontrada no texto extraído são descartadas antes de chegar ao usuário.
- Revisão **por item**: confirmar (com edição opcional dos campos), descartar, ou descartar todos os pendentes da sessão. Descartar um pai descarta em cascata os filhos pendentes. Confirmar um filho exige que o pai já exista na árvore real.
- A confirmação aplica o item **imediatamente** na árvore real, reutilizando as regras atuais (unicidade, auditoria e disparo da análise de seção e da expansão de consultas de `Branch`). Alterações em itens que mudaram desde a sugestão são rejeitadas por conflito.
- Novos endpoints REST sob `/tree-suggestion`, disponíveis para qualquer usuário autenticado.
- Escopo inicial: apenas PDF.

## Capabilities

### New Capabilities
- `check-tree-suggestions`: geração assistida por IA, a partir de um documento normativo em PDF, de sugestões revisáveis (dry-run) para criar ou enriquecer a árvore de verificação, com confirmação ou descarte por item.

### Modified Capabilities
<!-- Nenhuma: os CRUDs de Source/Typification/Taxonomy/Branch e o pipeline de ingestão não mudam de comportamento; são apenas reutilizados. -->

## Impact

- **Modelos e migrações**: novas tabelas para sessões de sugestão e itens sugeridos, com uma migração Alembic.
- **APIs**: novo router `lumina/routers/check_tree/tree_suggestions.py` (prefixo `/tree-suggestion`), registrado na aplicação.
- **Services**: novo `tree_suggestion_service` (ciclo de vida da sessão e revisão), que reutiliza `source_service`, `typification_service`, `taxonomy_service` e `branch_service` para aplicar as confirmações.
- **IA**: novo módulo de geração em `lumina/services/ai/` que reaproveita a extração de PDF existente (markdown, seções, páginas) e chama o LLM com saída estruturada. A telemetria usa o `run_logger`.
- **Configuração**: novos limites em `Settings` (tamanho máximo do arquivo, número máximo de páginas, timeout de processamento).
- **Custos**: cada sessão faz várias chamadas ao LLM, proporcionais ao tamanho do documento.
- **Breaking changes**: nenhuma; a mudança é puramente aditiva.
