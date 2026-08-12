# Arquitetura e Camadas de Teste (A Pirâmide Expandida)

Para garantir que a suíte de testes seja rápida e resiliente, o projeto divide os testes nas seguintes camadas:

## 1. Testes Unitários (Services)
- **Foco:** Regras de negócio, transições de estado, cálculos e decisões lógicas.
- **Como testar:** Devemos "mockar" (usar `unittest.mock` ou `pytest-mock`) dependências externas, como repositórios (acesso a dados) e chamadas a APIs de terceiros.
- **Onde:** `tests/unit/services/`

## 2. Testes de Integração (Repositories)
- **Foco:** Validar consultas no banco de dados. "Esta consulta retorna exatamente os dados que deveria retornar?"
- **Como testar:** Interagir com o banco de dados real via fixture (`session`). Importante testar consultas complexas (JOINs, GROUP BY, paginação). Consultas muito simples (ex: `session.add()`) podem ser omitidas desta camada se cobertas indiretamente.
- **Onde:** `tests/integration/repositories/`

## 3. Testes de Integração de API (Routers)
- **Foco:** Validar o fluxo de ponta a ponta na visão do cliente (HTTP).
- **Como testar:** Usar o `TestClient` (FastAPI). Requisição -> Router -> Service -> DB -> Resposta HTTP. Testamos jornadas de sucesso, erros 400/404 esperados e formatação do JSON de saída.
- **Onde:** `tests/api/routers/`

## 4. Testes de Segurança (Transversais)
- **Foco:** Restrição de acesso, autenticação e autorização.
- **Como testar:** Validar cenários de sem autenticação (401), sem permissão (403), e isolamento de tenant (usuário A tentando acessar recurso do usuário B). Geralmente rodam junto aos testes de API.

## 5. Testes de Regressão
- **Foco:** Evitar que bugs corrigidos voltem a ocorrer.
- **Como testar:** Ao corrigir um bug, deve-se criar um teste que originalmente falharia caso o bug estivesse presente, garantindo a permanência da correção.
