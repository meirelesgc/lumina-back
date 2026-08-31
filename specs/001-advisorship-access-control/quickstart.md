# Quickstart: Advisorship and Entity Access Control

## Overview

Este guia descreve como validar o controle de acesso, isolamento de dados e a demonstração visual de orientações do Lumina Back.

## 1. Pré-requisitos e Execução do Servidor

Certifique-se de que o banco de dados PostgreSQL e o Redis estejam em execução (via Docker Compose ou local):

```bash
# Iniciar serviços auxiliares
docker compose up -d db redis

# Executar a API em modo desenvolvimento
poetry run task run
```

A API estará acessível em `http://localhost:8000`.

---

## 2. Validação Manual via Página de Demonstração (Demo Interativa)

Acesse a página de demonstração servida pelo próprio FastAPI no navegador:

👉 **URL da Demo**: `http://localhost:8000/demos/advisorship/`

### Roteiro de Teste Interativo:

1. **Painel de Autenticação**:
   - Faça login com uma conta de **Orientador** (ex: `advisor@teste.com` / `senha`).
   - Observe o token JWT gerado e atribuído ao cabeçalho `Authorization: Bearer <token>`.
2. **Visão do Orientador**:
   - Clique em **"Listar Meus Orientandos"**: confirme que apenas os orientandos vinculados aparecem no cartão.
   - Clique em **"Listar Documentos (scope=advisees)"**: confirme que os trabalhos dos orientandos são listados.
3. **Alternância para Conta Isolada (Terceiro)**:
   - Clique em **"Simular Nova Conta (Usuário B)"**.
   - Clique em **"Listar Meus Projetos"** e **"Listar Meus Documentos"**: confirme que a lista retorna vazia (nenhum documento ou projeto de terceiros vazando).
   - Tente consultar o ID de um documento do Aluno: a página deve exibir o badge vermelho **`403 FORBIDDEN`**.

---

## 3. Validação Automatizada de Testes

Execute a suíte de testes de integração com isolamento transacional:

```bash
# Executar todos os testes de controle de acesso
poetry run pytest tests/integration/test_doc_access_control.py -vv

# Executar a suíte completa de testes do backend
poetry run task test
```
