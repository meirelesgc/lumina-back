## ADDED Requirements

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
