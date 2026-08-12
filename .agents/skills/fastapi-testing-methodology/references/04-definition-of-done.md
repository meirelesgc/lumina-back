# Definition of Done (Critérios de Parada)

Até onde testar? O limite é atingido quando a funcionalidade tem as evidências necessárias de segurança e comportamento esperados mitigando os riscos mapeados. 

Ao entregar testes para uma nova feature, os seguintes critérios devem ser validados:

- [ ] Todos os **requisitos funcionais relevantes** descritos para a feature possuem no mínimo um caso de teste que prova seu funcionamento.
- [ ] O **caminho crítico de sucesso** (Happy Path) está coberto ponta a ponta (Teste de API).
- [ ] As **regras de negócio críticas e condições de ramificação (Branches)** foram exercitadas de forma isolada (Testes Unitários).
- [ ] Os **erros esperados relevantes** (ex: falhas de validação, estados inválidos) mapeados na análise de risco possuem testes cobrindo a tratativa da exceção.
- [ ] O componente **Repository** possui testes dedicados caso execute queries complexas (com JOINs, condicionais múltiplos, agregações, etc). Consultas triviais podem pular este critério.
- [ ] Requisitos transversais de **Segurança/Autenticação** foram validados garantindo o bloqueio de acessos não autorizados ou sem permissão.
- [ ] Se o desenvolvimento resolve um defeito existente, **foi implementado um teste de regressão** para garantir que ele não reapareça.
- [ ] A cobertura geral de linhas/branches (auxiliar) está dentro dos *guardrails* estabelecidos, não indicando buracos graves em códigos cruciais.
