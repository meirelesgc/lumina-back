## ADDED Requirements

### Requirement: Acesso negado por padrão

O sistema SHALL exigir autenticação em toda rota HTTP e WebSocket, exceto `GET /health`, login, recuperação de senha, `POST /user` e as rotas de convite por token (consultar, registrar e recusar).

#### Scenario: Visitante chama rota protegida

- **WHEN** um visitante sem autenticação chama qualquer rota fora da lista pública
- **THEN** o sistema responde `401`

#### Scenario: Visitante consulta um convite

- **WHEN** um visitante envia `GET /invitations/{token}` com um token válido
- **THEN** o sistema responde `200`

### Requirement: Token de usuário removido

O sistema SHALL recusar com `401` o token de um usuário removido.

#### Scenario: Usuário removido usa token antigo

- **WHEN** um usuário removido chama `GET /user/my` com um token ainda não expirado
- **THEN** o sistema responde `401`

### Requirement: Dados de usuários restritos

O sistema SHALL permitir `GET /user` apenas a um `ADMIN`, e `GET /user/{id}` apenas ao titular ou a um `ADMIN`.

#### Scenario: Usuário comum lista usuários

- **WHEN** um usuário `DEFAULT` envia `GET /user`
- **THEN** o sistema responde `403`

#### Scenario: Usuário comum lê outra conta

- **WHEN** um usuário `DEFAULT` envia `GET /user/{id}` com o id de outra conta
- **THEN** o sistema responde `403`

#### Scenario: Administrador lista usuários

- **WHEN** um `ADMIN` envia `GET /user`
- **THEN** o sistema responde `200` com os usuários

### Requirement: Atualização preserva o nível omitido

O sistema SHALL manter o `access_level` atual quando `PUT /user` não trouxer esse campo.

#### Scenario: Administrador edita o próprio perfil sem informar o nível

- **WHEN** um `ADMIN` envia `PUT /user` com o próprio id e sem `access_level`
- **THEN** o sistema responde `200` e a conta continua `ADMIN`

### Requirement: Lista de orientadores

O sistema SHALL fornecer `GET /advisorship/advisors` a qualquer usuário autenticado, com id, nome, e-mail e ícone das contas `ADMIN` ativas, sem telefone.

#### Scenario: Orientando busca orientadores

- **WHEN** um usuário `DEFAULT` envia `GET /advisorship/advisors`
- **THEN** o sistema responde `200` só com contas `ADMIN` ativas, e nenhum item traz `phone_number`

### Requirement: Criação de vínculo direto

O sistema SHALL permitir `POST /advisorship` a um `ADMIN`, ou a quem for o próprio `advisee_id` com `advisor_id` de uma conta `ADMIN`, e SHALL responder `403` aos demais sem gravar o vínculo.

#### Scenario: Usuário se declara orientador de outro

- **WHEN** um usuário `DEFAULT` envia `POST /advisorship` com `advisor_id` igual ao próprio id e `advisee_id` de outra pessoa
- **THEN** o sistema responde `403` e nenhum vínculo é gravado

#### Scenario: Orientando escolhe um orientador

- **WHEN** um usuário `DEFAULT` envia `POST /advisorship` sendo o `advisee_id`, com um `ADMIN` como `advisor_id`
- **THEN** o sistema responde `201` com o vínculo ativo

#### Scenario: Orientando escolhe orientador sem nível de administrador

- **WHEN** um usuário `DEFAULT` envia `POST /advisorship` sendo o `advisee_id`, com outra conta `DEFAULT` como `advisor_id`
- **THEN** o sistema responde `403`

#### Scenario: Administrador cria vínculo entre terceiros

- **WHEN** um `ADMIN` envia `POST /advisorship` com orientador e orientando quaisquer
- **THEN** o sistema responde `201`

### Requirement: Projeto do vínculo pertence a uma das partes

O sistema SHALL responder `403` a `POST /advisorship`, `PUT /advisorship/{id}` e `POST /invitations` com projeto que não pertença ao orientador nem ao orientando, salvo quando quem pede for `ADMIN`.

#### Scenario: Orientando usa projeto de terceiro

- **WHEN** um usuário `DEFAULT` cria um vínculo com `project_id` de um projeto de outra pessoa
- **THEN** o sistema responde `403`

### Requirement: Encerramento e reativação de vínculo

O sistema SHALL permitir `DELETE /advisorship/{id}` às duas partes e a um `ADMIN`, e SHALL permitir que só um `ADMIN` devolva um vínculo encerrado para `ACTIVE`.

#### Scenario: Orientando encerra o vínculo

- **WHEN** o orientando envia `DELETE /advisorship/{id}` do próprio vínculo
- **THEN** o sistema responde `200` e o orientador perde o acesso

#### Scenario: Orientador sem nível de administrador tenta reativar

- **WHEN** o orientador `DEFAULT` envia `PUT /advisorship/{id}` com `status` igual a `ACTIVE` num vínculo `CANCELLED`
- **THEN** o sistema responde `403` e o vínculo continua `CANCELLED`

### Requirement: Vínculo encerrado não dá acesso

O sistema SHALL considerar só vínculos `ACTIVE` ao liberar documentos, projetos e listagens do orientando.

#### Scenario: Ex-orientador lista documentos

- **WHEN** um orientador `DEFAULT` com vínculo `CANCELLED` ou `COMPLETED` envia `GET /advisorship/advisees/{id}/documents`
- **THEN** o sistema responde `403`

#### Scenario: Orientador ativo em outro projeto

- **WHEN** um orientador tem vínculo `ACTIVE` com o aluno em outro projeto e envia `GET /advisorship/advisees/{id}/documents`
- **THEN** o sistema responde `200`

### Requirement: Aceite reativa vínculo encerrado

O sistema SHALL devolver para `ACTIVE` o vínculo encerrado do mesmo orientador, orientando, projeto e papel quando o orientando aceitar um convite ou escolher de novo esse orientador.

#### Scenario: Orientando aceita convite após vínculo cancelado

- **WHEN** o orientando aceita um convite de quem já foi seu orientador em vínculo `CANCELLED`
- **THEN** o vínculo volta a `ACTIVE` e o orientador lê os documentos do orientando

### Requirement: Convite restrito ao administrador

O sistema SHALL permitir `POST /invitations` apenas a um `ADMIN`.

#### Scenario: Usuário comum envia convite

- **WHEN** um usuário `DEFAULT` envia `POST /invitations`
- **THEN** o sistema responde `403` e nenhum convite é gravado

### Requirement: Dados de documento seguem o acesso ao documento

O sistema SHALL exigir acesso de leitura ao documento para listar releases, exportar PDF, ler e criar mensagens, abrir conversa, usar o assistente, ler o contexto acadêmico e conectar ao WebSocket do documento.

#### Scenario: Usuário sem acesso lista releases

- **WHEN** um usuário sem acesso ao documento envia `GET /doc/{doc_id}/release`
- **THEN** o sistema responde `403`

#### Scenario: Usuário sem acesso posta mensagem

- **WHEN** um usuário sem acesso ao documento envia `POST /doc/{doc_id}/message`
- **THEN** o sistema responde `403` e nenhuma mensagem é gravada

#### Scenario: Orientador ativo revisa

- **WHEN** um orientador com vínculo `ACTIVE` envia `POST /doc/{doc_id}/message`
- **THEN** o sistema responde `201`

#### Scenario: WebSocket sem acesso

- **WHEN** um usuário sem acesso ao documento conecta ao WebSocket do documento
- **THEN** o sistema fecha a conexão sem entrar no canal

### Requirement: Escrita em releases

O sistema SHALL permitir criar release ao autor, a um editor ou a um `ADMIN`, e remover release ao autor ou a um `ADMIN`.

#### Scenario: Usuário sem vínculo envia release

- **WHEN** um usuário sem acesso ao documento envia `POST /doc/{doc_id}/release`
- **THEN** o sistema responde `403`

#### Scenario: Editor remove release

- **WHEN** um editor envia `DELETE /doc/{doc_id}/release/{release_id}`
- **THEN** o sistema responde `403`

### Requirement: Mensagens pertencem ao autor

O sistema SHALL permitir editar ou apagar uma mensagem apenas ao autor dela ou a um `ADMIN`.

#### Scenario: Outro usuário edita mensagem

- **WHEN** um usuário com acesso ao documento envia `PUT /doc/message` para mensagem de outra pessoa
- **THEN** o sistema responde `403` e a mensagem não muda

### Requirement: Documento de projeto exige acesso ao projeto

O sistema SHALL responder `403` a `POST /doc` com `project_document_id` de projeto ao qual o usuário não tem acesso.

#### Scenario: Usuário liga documento a projeto alheio

- **WHEN** um usuário envia `POST /doc` com documento de projeto de outra pessoa
- **THEN** o sistema responde `403` e nenhum documento é criado

### Requirement: Arquivos seguem o recurso dono

O sistema SHALL servir `/uploads/{arquivo}` a quem pode ler o documento do release ou o projeto do arquivo, a qualquer autenticado para ícones e fontes, e só a um `ADMIN` para os demais arquivos.

#### Scenario: Autor baixa o próprio release

- **WHEN** o autor pede o arquivo do release pela URL de `file_path`, com o cookie de sessão
- **THEN** o sistema responde `200` com o arquivo

#### Scenario: Usuário sem acesso pede o arquivo

- **WHEN** um usuário sem acesso ao documento pede o arquivo do release
- **THEN** o sistema responde `403`

#### Scenario: Caminho fora da pasta de uploads

- **WHEN** um `ADMIN` pede um caminho com `..` que sai da pasta de uploads
- **THEN** o sistema responde `404`

### Requirement: Configurador restrito ao administrador

O sistema SHALL exigir `ADMIN` para escrever em tipificações, taxonomias, ramos, fontes, grupos, itens, anexos de estudo e templates, e para todas as rotas de sugestão de árvore. Qualquer autenticado SHALL continuar lendo os demais dados do configurador.

#### Scenario: Usuário comum cria tipificação

- **WHEN** um usuário `DEFAULT` envia `POST /typification`
- **THEN** o sistema responde `403` e nada é gravado

#### Scenario: Usuário comum altera grupo

- **WHEN** um usuário `DEFAULT` envia `PUT /document-group`
- **THEN** o sistema responde `403`

#### Scenario: Usuário comum lista grupos

- **WHEN** um usuário `DEFAULT` envia `GET /document-group`
- **THEN** o sistema responde `200`

#### Scenario: Administrador cria tipificação

- **WHEN** um `ADMIN` envia `POST /typification`
- **THEN** o sistema responde `201`

### Requirement: Resultados de conformidade pertencem ao dono

O sistema SHALL mostrar e remover resultados de ABNT e template apenas para quem os criou ou para um `ADMIN`.

#### Scenario: Outro usuário lê resultado

- **WHEN** um usuário `DEFAULT` envia `GET /abnt/results/{id}` de resultado de outra pessoa
- **THEN** o sistema responde `403`

#### Scenario: Listagem filtra por dono

- **WHEN** um usuário `DEFAULT` envia `GET /abnt/results`
- **THEN** a resposta traz só os resultados criados por ele

### Requirement: Rotas de sistema restritas ao administrador

O sistema SHALL exigir `ADMIN` em `/stats` e `/system-settings`.

#### Scenario: Usuário comum lê estatísticas

- **WHEN** um usuário `DEFAULT` envia `GET /stats/kpis`
- **THEN** o sistema responde `403`

### Requirement: Provisionamento do primeiro administrador

O sistema SHALL fornecer um comando de linha que promove a `ADMIN` uma conta ativa pelo e-mail, e que falha sem alterar nada quando a conta não existe.

#### Scenario: Operador promove uma conta

- **WHEN** quem opera o ambiente roda o comando com o e-mail de uma conta ativa
- **THEN** a conta passa a `ADMIN`

#### Scenario: E-mail inexistente

- **WHEN** quem opera o ambiente roda o comando com um e-mail sem conta
- **THEN** o comando termina com erro e nenhuma conta muda
