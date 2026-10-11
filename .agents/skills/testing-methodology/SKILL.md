---
name: testing-methodology
description: Metodologia para planejar, escrever e revisar testes a partir de jornadas de usuário. Use ao criar, alterar, revisar ou planejar testes (inclusive nas tarefas do Spec Kit), em qualquer stack. Primeiro descreve o comportamento esperado do usuário, depois monta o teste sobre esse caminho e completa com testes focados guiados por risco.
---

# Metodologia de testes orientada a jornadas

Um teste existe para provar que alguém consegue fazer o que precisa e que o
sistema impede o que não deve acontecer. A cobertura de linhas é um indicador,
não um objetivo.

O ponto de partida é a **jornada**: quem usa o sistema, o que quer conseguir,
o que faz em cada passo e o que espera ver. O teste de jornada percorre esse
caminho pela interface pública. Os testes focados cobrem depois as regras,
os erros e os limites que não cabem na jornada.

## Fluxo de trabalho

1. **Descreva a jornada antes do código.** Escreva em prosa o ator, o
   objetivo, o estado inicial, os passos e o que o usuário observa em cada
   um. Use o modelo de [`templates/jornada.md`](templates/jornada.md) e as
   regras de [`references/01-jornadas.md`](references/01-jornadas.md). Se não
   conseguir dizer o que o usuário espera ver, o requisito ainda está
   ambíguo: pergunte antes de testar.
2. **Monte o teste sobre esse caminho.** Um teste por jornada, com os passos
   numerados nos comentários na mesma ordem da descrição, usando só a
   interface pública. Veja [`templates/test_jornada_exemplo.py`](templates/test_jornada_exemplo.py).
3. **Complete com testes focados guiados por risco.** Cada desvio relevante
   (erro, permissão negada, estado inválido, concorrência) vira um teste
   pequeno e separado, na camada mais barata que ainda prova o comportamento.
   Veja [`references/02-camadas-e-risco.md`](references/02-camadas-e-risco.md).
4. **Pare quando os critérios forem atendidos.** Use
   [`references/03-criterios-de-parada.md`](references/03-criterios-de-parada.md).

## Regras essenciais

- A jornada fala a língua do usuário: "o proponente envia a proposta", não
  "POST retorna 201".
- O teste de jornada usa só o que o usuário usa: cadastro, login, chamadas
  públicas, listagens. Consultar o banco diretamente é exceção, reservada a
  efeitos que o usuário não consegue observar, e deve ser comentada.
- Cada passo verifica o que o usuário veria naquele momento (status, dados
  na resposta, tarefa que aparece ou some), não só o resultado final.
- Troca de ator é explícita: sair e entrar como outra pessoa, como acontece
  no uso real.
- O estado inicial é realista. Prefira partir do mesmo provisionamento de um
  ambiente novo a montar registros soltos com identificadores inventados.
- Desvios importantes viram jornadas próprias ou testes focados. Não
  acumule caminhos alternativos dentro de um único teste.
- O nome do teste descreve o objetivo do usuário e o desfecho
  (`test_triagem_pede_revisao_e_proponente_reenvia`).
- Serviços externos (e-mail, IA, armazenamento) usam substitutos
  determinísticos. Veja [`references/05-ia.md`](references/05-ia.md) para IA.

## No Spec Kit

- Cada história de usuário da `spec.md` gera ao menos uma jornada. A
  descrição da jornada pode ser derivada dos cenários de aceitação.
- Em `tasks.md`, a tarefa da jornada vem antes das tarefas de implementação
  da história, seguida das tarefas dos testes focados. Cada tarefa indica um
  resultado verificável e o caminho do arquivo de teste.

## Referências

1. [Jornadas: como descrever e testar](references/01-jornadas.md)
2. [Camadas e matriz de risco](references/02-camadas-e-risco.md)
3. [Critérios de parada](references/03-criterios-de-parada.md)
4. [Armadilhas comuns](references/04-armadilhas.md)
5. [Testes de sistemas com IA](references/05-ia.md)
6. [Aplicação neste repositório (pi\*VMA)](references/06-projeto-pivma.md)
