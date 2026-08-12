# Cobertura de Código e Matriz de Risco

**O objetivo dos testes não é maximizar cegamente a cobertura de código, mas sim prover evidências de que os comportamentos funcionam e os riscos estão mitigados.** A cobertura de linha (Line Coverage) atua apenas como um indicador e *guardrail* (ex: manter acima de 80%).

## 1. Branch Coverage e Comportamento
Onde há regras de negócio e tomada de decisões lógicas, a simples passagem por uma linha não é suficiente. Deve-se observar a cobertura de **Branches** e avaliar ativamente o que acontece quando "algo dá errado".

Para cada comportamento importante, questione e defina quais cenários devem ser cobertos:
- Entrada válida e inválida.
- Estados de recursos inválidos ou conflitantes.
- Recursos ou dependências inexistentes.
- Falta de permissões de acesso.

## 2. Matriz de Risco (Profundidade do Teste)
A profundidade do esforço de teste segue a criticidade da funcionalidade:

| Funcionalidade (Exemplo) | Risco | Camadas a Testar |
| :--- | :---: | :--- |
| Login / Regras Críticas | **Crítico** | Unit, Integration, API Integration, Security |
| Transações Importantes | **Alto** | Unit, Integration, API Integration |
| Buscas e Leituras | **Médio** | Unit, Integration (se query complexa) |
| CRUDs Simples / Health | **Baixo** | API Integration (cobre o básico indiretamente) |

## 3. O que ignorar na Métrica (Omissis)
Arquivos como `models.py` e `schemas.py` só devem ser excluídos da validação de cobertura automática (via `.coveragerc`) **se forem puramente declarativos** ou gerados automaticamente.
Se o modelo ou schema tiver código real (ex: Pydantic `@model_validator` ou um `@property` do SQLAlchemy), essa lógica deve sim ser testada, portanto a exclusão total por nome de arquivo não é recomendada.
