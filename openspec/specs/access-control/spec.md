# access-control Specification

## Purpose
Define quem pode executar cada operação da API do Lumina, começando pela criação de contas, pela remoção de usuários e pela leitura da trilha de auditoria.

## Requirements

### Requirement: Cadastro público cria contas sem privilégio

O sistema SHALL criar como `DEFAULT` toda conta vinda de `POST /user`, com ou sem autenticação, e SHALL ignorar qualquer `access_level` enviado no corpo.

#### Scenario: Visitante pede nível de administrador

- **WHEN** um visitante sem autenticação envia `POST /user` com `access_level` igual a `ADMIN`
- **THEN** o sistema responde `201` e a conta criada tem `access_level` igual a `DEFAULT`

#### Scenario: Visitante se cadastra sem informar o nível

- **WHEN** um visitante sem autenticação envia `POST /user` sem `access_level`
- **THEN** o sistema responde `201` e a conta criada tem `access_level` igual a `DEFAULT`

#### Scenario: Administrador promove uma conta

- **WHEN** um `ADMIN` envia `PUT /user` com `access_level` igual a `ADMIN` para outra conta
- **THEN** o sistema responde `200` e a conta passa a ter `access_level` igual a `ADMIN`

### Requirement: Remoção de usuário restrita ao titular e ao administrador

O sistema SHALL permitir `DELETE /user/{id}` apenas ao próprio usuário ou a um `ADMIN`, e SHALL responder `403` aos demais usuários autenticados sem alterar a conta.

#### Scenario: Usuário comum tenta remover outra pessoa

- **WHEN** um usuário `DEFAULT` envia `DELETE /user/{id}` com o id de outra conta
- **THEN** o sistema responde `403` e a conta continua ativa

#### Scenario: Usuário remove a própria conta

- **WHEN** um usuário `DEFAULT` envia `DELETE /user/{id}` com o próprio id
- **THEN** o sistema responde `204`

#### Scenario: Administrador remove outra conta

- **WHEN** um `ADMIN` envia `DELETE /user/{id}` com o id de outra conta
- **THEN** o sistema responde `204` e a conta deixa de aparecer em `GET /user`

### Requirement: Trilha de auditoria restrita ao administrador

O sistema SHALL permitir `GET /audit-log` apenas a um `ADMIN`.

#### Scenario: Visitante consulta a auditoria

- **WHEN** um visitante sem autenticação envia `GET /audit-log`
- **THEN** o sistema responde `401` e não devolve registros

#### Scenario: Usuário comum consulta a auditoria

- **WHEN** um usuário `DEFAULT` envia `GET /audit-log`
- **THEN** o sistema responde `403` e não devolve registros

#### Scenario: Administrador consulta a auditoria

- **WHEN** um `ADMIN` envia `GET /audit-log`
- **THEN** o sistema responde `200` com os registros

### Requirement: Níveis de acesso aceitos

O sistema SHALL aceitar apenas `DEFAULT` e `ADMIN` como `access_level`, e SHALL responder `422` a qualquer outro valor enviado em `PUT /user`.

#### Scenario: Administrador tenta usar um nível removido

- **WHEN** um `ADMIN` envia `PUT /user` com `access_level` igual a `AUDITOR`
- **THEN** o sistema responde `422` e a conta mantém o nível anterior

#### Scenario: Administrador define um nível aceito

- **WHEN** um `ADMIN` envia `PUT /user` com `access_level` igual a `ADMIN`
- **THEN** o sistema responde `200` e a conta passa a ter `access_level` igual a `ADMIN`

### Requirement: Contas com níveis removidos passam a DEFAULT

A migração SHALL converter para `DEFAULT` toda conta com `access_level` igual a `AUDITOR` ou `ANALYST`, e SHALL manter as contas `ADMIN` e `DEFAULT`.

#### Scenario: Migração de conta com nível removido

- **WHEN** a migração roda sobre uma base com contas `AUDITOR`, `ANALYST` e `ADMIN`
- **THEN** as contas `AUDITOR` e `ANALYST` ficam com `DEFAULT` e a conta `ADMIN` continua com `ADMIN`
