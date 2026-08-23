# 01 - Testes de Caracterização (Characterization Testing)

## O que são Testes de Caracterização?
Testes de caracterização (*Characterization Tests*) têm uma finalidade bem específica: **registrar o comportamento real que o sistema possui hoje**, e não o que idealmente achamos que ele deveria ter. Eles funcionam como uma **fotografia de alta fidelidade** do sistema antes de iniciarmos qualquer alteração estrutural.

```text
Entrada A  ──>  Resultado X (observado)
Entrada B  ──>  Resultado Y (observado)
Entrada C  ──>  Resultado Z (observado)
```

## Por que usá-los em Refatorações Grandes?
Em bases de código existentes ou herdadas, frequentemente existe um **dilema circular**:
> *"Eu preciso alterar o código para conseguir testá-lo melhor, mas preciso de testes antes de poder alterá-lo com segurança."*

Os testes de caracterização quebram esse ciclo porque:
1. Não exigem que o código interno esteja desacoplado ou "bonito".
2. Testam no nível mais estável (rotas HTTP, contratos de payload e efeitos observáveis).
3. Permitem responder à pergunta crucial: *"Após essa mudança estrutural, o sistema continua se comportando exatamente da mesma maneira?"*

---

## Diretrizes Práticas de Implementação

### 1. Foque Apenas nos Fluxos Afetados
Não tente criar cobertura de 100% no sistema todo antes de refatorar. Isole os fluxos que de fato tocam o conceito a ser modificado.
* *Exemplo*: Se estamos removendo `Unit`, identificamos que os fluxos afetados eram:
  * Criação e consulta de Documentos (`/doc`);
  * Notificações de mudança de status no Kanban (`/doc/{id}/status/*`);
  * CRUD de Usuários (`/user`);
  * Métricas do Dashboard (`/stats/kpis`).

### 2. Capture Entradas e Respostas Reais da API
* Execute as chamadas HTTP com autenticação real ou simulada via `TestClient`.
* Valide códigos de status HTTP (`201 CREATED`, `200 OK`, etc.).
* Valide que os campos esperados no contrato JSON estão presentes.
* Valide efeitos colaterais críticos (ex: disparos de mensagens para filas RabbitMQ via mocks assíncronos).

### 3. Aceite Peculiaridades do Legado Inicialmente
Se o sistema legado exige um campo estranho ou um valor específico no banco para funcionar (ex: o usuário precisar ter uma `unit_id` atribuída para não disparar erro `NOT NULL`), **registre essa exigência no teste inicial**.
Conforme os passos de refatoração avançarem, você ajustará essas exigências.

### 4. Garanta 100% Verde Antes de Avançar
Nunca inicie a alteração dos modelos ou regras de negócio enquanto os testes de caracterização não estiverem passando com 100% de sucesso.
