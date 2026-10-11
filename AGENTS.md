# AGENTS.md

As skills deste projeto ficam em `.agents/skills/`. Antes de cada tarefa, veja
se alguma se aplica. Se sim, leia o `SKILL.md` inteiro e siga as instruções,
incluindo os arquivos de `references/` e `templates/` que ele indicar.

Sugira a skill por conta própria. Se o usuário pular uma etapa (começar a
codar sem plano, mexer em código sem teste, escrever um texto sem revisão),
aponte a skill que cobre aquele ponto antes de seguir.

## Quando usar cada skill

### Código: `karpathy-guidelines`

Use ao escrever, revisar ou refatorar código. A skill pede mudanças cirúrgicas,
a solução mais simples que resolve o problema, suposições explícitas e um
critério de sucesso verificável. Se o pedido abrir espaço para abstração ou
refatoração fora do escopo, pergunte antes.

### Testes: `testing-methodology`

Use sempre que um teste for criado, alterado, revisado ou planejado. Comece
pela jornada do usuário, escreva o teste sobre esse caminho e complete com
testes focados nos riscos. Se uma mudança de comportamento chegar sem teste,
sugira a skill.

### Desenvolvimento: OpenSpec

Funcionalidade nova ou mudança de comportamento passa pelo OpenSpec:

| Etapa | Skill |
| :--- | :--- |
| Explorar uma ideia ou um problema | `openspec-explore` |
| Propor a mudança com todos os artefatos | `openspec-propose` |
| Revisar o plano de uma mudança existente | `openspec-update-change` |
| Implementar as tarefas | `openspec-apply-change` |
| Levar as delta specs para as specs principais | `openspec-sync-specs` |
| Arquivar a mudança concluída | `openspec-archive-change` |

Regras:

1. **Feche o plano antes de implementar.** Pergunte ao usuário sobre todo
   ponto pendente ou ambíguo e registre as respostas nos artefatos. Só comece
   `openspec-apply-change` quando o plano não tiver lacunas.
2. **Guarde débitos em issues.** Se um ponto não for resolvido nesta mudança,
   proponha abrir uma issue no repositório com o modelo de
   `.github/ISSUE_TEMPLATE/demanda.md` e cite a issue nos artefatos.
3. **Commite a documentação separada da implementação.** Os artefatos do
   OpenSpec (`docs(openspec): ...`) vão em um commit; o código e os testes
   (`feat(...)`, `fix(...)`) vão em outro.

### Texto: `stop-slop`

Use ao redigir ou revisar prosa: documentação, artefatos do OpenSpec, issues,
descrições de PR e mensagens de commit. Corte enchimento, prefira voz ativa,
nomeie as coisas e não use travessões.

## Skills novas

Se aparecer uma pasta em `.agents/skills/` fora desta lista, leia o frontmatter
do `SKILL.md` para saber quando usá-la e acrescente-a aqui.
