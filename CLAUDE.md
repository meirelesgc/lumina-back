@AGENTS.md

# Skills

As skills deste projeto ficam em `.agents/skills/` (padrão compartilhado com
outros agentes), não em `.claude/skills/`. Antes de começar uma tarefa, veja se
alguma skill abaixo se aplica. Se sim, leia o `SKILL.md` dela por inteiro e siga
as instruções. Leia os arquivos de `references/` e `templates/` quando o
`SKILL.md` indicar.

| Skill | Quando usar |
| :--- | :--- |
| `karpathy-guidelines` | Ao escrever, revisar ou refatorar código. |
| `testing-methodology` | Ao criar, alterar, revisar ou planejar testes. |
| `stop-slop` | Ao redigir ou revisar textos em prosa (docs, PRs, mensagens). |
| `openspec-explore` | Para explorar uma ideia ou um problema antes ou durante uma mudança. |
| `openspec-propose` | Para propor uma mudança nova, com todos os artefatos. |
| `openspec-update-change` | Para revisar os artefatos de planejamento de uma mudança existente. |
| `openspec-apply-change` | Para implementar as tarefas de uma mudança do OpenSpec. |
| `openspec-sync-specs` | Para sincronizar delta specs de uma mudança com as specs principais. |
| `openspec-archive-change` | Para arquivar uma mudança concluída. |

Se aparecer uma pasta em `.agents/skills/` que não está nesta tabela, leia o
frontmatter do `SKILL.md` dela para saber quando usar e adicione-a aqui.
