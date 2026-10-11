# Jornadas: como descrever e testar

## O que é uma jornada

Uma jornada é o caminho que um ou mais usuários percorrem para atingir um
objetivo real no sistema. Ela tem:

- **Atores:** quem participa, pelo papel que exerce (proponente, revisor,
  administrador), não pela permissão técnica.
- **Objetivo:** o que o ator quer conseguir, em uma frase.
- **Estado inicial:** o que já existe antes do primeiro passo (ambiente
  recém-provisionado, conta criada, processo em certa etapa).
- **Passos:** ações na ordem em que o usuário as faria, cada uma com o que ele
  espera observar em seguida.
- **Desfecho:** como o usuário sabe que conseguiu, e o que muda para os
  outros atores.
- **Desvios:** caminhos alternativos relevantes (recusa, erro, falta de
  permissão) que serão testados à parte.

## Como escrever a descrição

1. Parta da fonte do requisito: história de usuário, cenário de aceitação,
   issue ou fluxo do protótipo. Cite a fonte na descrição.
2. Escreva cada passo com verbo de ação do ator e a expectativa observável:
   "O revisor abre a lista de pendências e vê a proposta como pronta para
   triagem."
3. Registre o que cada ator **não** deve ver ou conseguir quando isso fizer
   parte do comportamento (ex.: o proponente não vê o parecer interno).
4. Se um passo depende de uma regra que você não sabe explicar, pare e
   pergunte. A jornada não deve preencher lacunas de requisito com suposição.

A descrição vai na docstring do módulo de teste. Assim ela fica junto do
código que a verifica e é revisada no mesmo PR.

## Como transformar em teste

- Um teste por jornada. O corpo segue os passos numerados, com um comentário
  curto antes de cada bloco (`# 2. O revisor pede ajustes.`).
- Use a mesma interface que o cliente real usa. Em uma API, isso significa
  autenticar como o usuário, enviar os cabeçalhos que o cliente enviaria e
  ler as respostas públicas.
- Verifique em cada passo o que a descrição diz que o usuário observa. Se a
  descrição promete algo, o teste confere.
- Troque de ator explicitamente (sair, entrar como outro). Não reutilize a
  sessão de um ator para agir como outro.
- Extraia ações repetidas em helpers com nome de ação do usuário
  (`cadastrar`, `entrar`, `enviar_proposta`). Os helpers podem conter
  asserts do status esperado; a jornada mantém os asserts do comportamento.
- Consultar o armazenamento diretamente só quando o efeito não é observável
  pela interface (ex.: estado interno de uma fase). Comente o motivo.

## Quando usar outra forma de teste

A jornada prova que o caminho principal funciona de ponta a ponta. Ela não é
o lugar para:

- cada combinação de entrada inválida;
- cada status de erro;
- cada papel sem permissão;
- concorrência, paginação, ordenação e limites.

Esses casos viram testes focados e independentes (ver
`02-camadas-e-risco.md`). Uma jornada para um desvio só se justifica quando o
desvio é, ele mesmo, um caminho que o usuário percorre até o fim (ex.: "a
triagem pede revisão, o proponente reenvia e a nova versão é aprovada").

## Sinais de uma jornada mal escrita

- Os passos descrevem chamadas técnicas, não ações do usuário.
- O teste cria registros diretamente no banco em vez de usar a interface.
- Só o resultado final é verificado.
- Vários desvios estão encadeados no mesmo teste.
- O teste passa mesmo que um ator veja algo que não deveria ver.
