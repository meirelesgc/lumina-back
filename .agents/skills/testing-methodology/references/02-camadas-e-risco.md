# Camadas e matriz de risco

## Camadas

Escolha a camada mais barata que ainda prova o comportamento.

| Camada | Prova | Quando usar |
|---|---|---|
| **Jornada** | Um objetivo de usuário funciona de ponta a ponta pela interface pública, com os atores reais | Toda história de usuário com fluxo entre telas, papéis ou etapas |
| **Contrato da interface** | Uma rota ou operação responde corretamente a um caso específico: sucesso, cada erro, formato da resposta | Cada status de erro, validação, formato de listagem, autorização por rota |
| **Integração com armazenamento** | Consultas e restrições do banco se comportam como esperado | Consultas com junções, agregações, filtros combinados, restrições de integridade, migrações |
| **Unitário** | Uma regra isolada decide corretamente | Cálculos, transições de estado, validações puras, funções sem I/O |
| **Regressão** | Um defeito corrigido não volta | Todo bug corrigido, na camada onde ele foi reproduzido |

Segurança é transversal: sem autenticação, sem permissão e acesso a recurso de
outro usuário ou grupo são testados como contratos da interface, e o
isolamento principal também aparece na jornada quando faz parte do fluxo.

## Matriz de risco

A profundidade segue o impacto de uma falha.

| Risco | Exemplos | O que testar |
|---|---|---|
| **Crítico** | Autenticação, autorização, isolamento de dados, cegamento, decisões regulatórias, auditoria | Jornada + contrato de cada erro e de cada perfil negado + unitário das regras + regressão |
| **Alto** | Transições de estado, fluxos com vários atores, envio de notificações, integrações | Jornada + contrato dos erros relevantes + unitário das regras com ramificações |
| **Médio** | Listagens, filtros, buscas, relatórios | Contrato (filtros, ordenação, paginação) + integração quando a consulta é complexa |
| **Baixo** | CRUD simples, verificação de saúde | Contrato do caminho de sucesso e da validação principal |

## Perguntas para cada comportamento

- O que acontece com entrada válida? E inválida?
- E se o recurso não existe, está inativo ou em estado incompatível?
- Quem não deveria conseguir? O que essa pessoa recebe?
- O que outro usuário ou grupo consegue ver?
- O que fica registrado (auditoria, linha do tempo)?
- O que acontece se duas pessoas agirem ao mesmo tempo?

Cada resposta relevante vira um teste separado. Não agrupe resultados
diferentes em um único teste.

## Cobertura de código

A cobertura de linhas e ramificações serve para encontrar buracos, não para
fechar a tarefa. Código declarativo puro pode ficar fora da métrica; código
com lógica (validadores, propriedades calculadas) é testado.
