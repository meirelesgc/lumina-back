## Why

Cada rota do Lumina declara a própria regra de acesso, então uma rota nova nasce aberta e as regras divergem. Rotas de documentos, mensagens, arquivos e dados globais ainda aceitam anônimos ou qualquer usuário autenticado. Esta mudança nega acesso por padrão, concentra as regras em um módulo e resolve as issues #31, #32 e #33.

## What Changes

- **BREAKING**: toda rota exige autenticação, exceto a lista explícita de rotas públicas.
- **BREAKING**: `GET /user` passa a exigir `ADMIN`, e `GET /user/{id}` passa a exigir o titular ou um `ADMIN`.
- Nova rota `GET /advisorship/advisors`, que lista os orientadores disponíveis para o onboarding.
- **BREAKING**: escrita em tipificações, taxonomias, ramos, fontes, grupos, anexos de estudo, sugestões de árvore e templates exige `ADMIN`.
- **BREAKING**: `/stats` e `/system-settings` exigem `ADMIN`.
- **BREAKING**: releases, mensagens, conversas, PDFs, contexto acadêmico e WebSockets exigem acesso ao documento. Editar ou apagar mensagem exige o autor ou um `ADMIN`.
- **BREAKING**: resultados de ABNT e template ficam visíveis e removíveis só pelo dono ou por um `ADMIN`.
- **BREAKING**: arquivos em `/uploads` mantêm a URL, mas exigem autenticação e acesso ao recurso dono do arquivo.
- **BREAKING**: criar vínculo direto exige `ADMIN`, ou o orientando em nome próprio com orientador `ADMIN`. Enviar convite exige `ADMIN`.
- Orientando pode encerrar o próprio vínculo. Só `ADMIN` reativa vínculo encerrado.
- Vínculo encerrado deixa de dar acesso em toda listagem, e aceitar convite reativa o vínculo encerrado.
- Token de usuário removido deixa de valer, e `PUT /user` sem `access_level` mantém o nível.
- Novo comando `python -m lumina.scripts.promote_admin <email>`, que promove a primeira conta `ADMIN` de um ambiente.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `access-control`: passa a cobrir a política geral, documentos, arquivos, orientação, convites, configurador e sistema.

## Impact

- **Código**: novo `lumina/services/access_service.py`, routers, services de documento, mensagem, orientação, convite e conformidade, `advisorship_repo`, `lumina/core/security.py`, `lumina/app.py` e novo script.
- **Banco**: nenhuma migração.
- **Frontend**: o onboarding do orientando precisa trocar `GET /user` por `GET /advisorship/advisors`. O documento para o time do front descreve a troca. Sem ela, usuários `DEFAULT` recebem `403` nessa etapa.
- **Documentação**: `docs/orientacao-academica.md` e `docs/governanca.md`.
- **Issues**: fecha #31, #32 e #33.
