# Armadilhas comuns

## Payload adivinhado

Montar o corpo da requisição pelo senso comum costuma gerar erro de
validação ou, pior, um teste que passa pelo motivo errado.
**Faça assim:** leia o schema de entrada antes de escrever a chamada.

## Identificadores inventados

Usar um identificador aleatório como chave estrangeira (`created_by`,
`process_id`) quebra a integridade do banco ou testa um cenário impossível.
**Faça assim:** crie as entidades relacionadas pela interface ou por
factories persistidas, e use os identificadores que elas devolvem.

## Estado montado por fora da interface na jornada

Inserir registros direto no banco no meio de uma jornada esconde defeitos no
caminho real.
**Faça assim:** na jornada, todo estado nasce de uma ação do usuário ou do
provisionamento de um ambiente novo.

## Verificar só o final

Um teste que confere apenas o último estado não mostra onde o fluxo quebrou
e deixa passar efeitos intermediários errados.
**Faça assim:** verifique o que o usuário observa em cada passo.

## Ator errado

Agir com a sessão de um usuário enquanto o passo pertence a outro faz a
autorização parecer correta quando não está.
**Faça assim:** saia e entre como o ator de cada passo.

## Tempo e aleatoriedade

Prazos, expiração e ordenação por data tornam testes instáveis.
**Faça assim:** controle o relógio e a aleatoriedade por fixture ou injeção,
e não dependa da ordem de inserção sem ordenação explícita.

## Serviços externos reais

Chamadas reais a e-mail, IA ou armazenamento deixam a suíte lenta, cara e
instável.
**Faça assim:** use substitutos determinísticos injetados pela aplicação.

## Fixtures assíncronas mal declaradas

Em pytest com asyncio, uma fixture `async def` decorada só com
`@pytest.fixture` devolve uma corrotina não aguardada e pode corromper a
transação dos testes seguintes.
**Faça assim:** use `@pytest_asyncio.fixture` em fixtures assíncronas.

## Nomes de arquivo genéricos

Arquivos como `test_api.py` em pastas diferentes colidem na importação.
**Faça assim:** inclua o domínio no nome (`test_triage_decision.py`).

## Isolamento caro

Recriar o schema a cada teste deixa a suíte lenta e esgota conexões.
**Faça assim:** crie o schema uma vez por sessão e isole cada teste com
transação e rollback.
