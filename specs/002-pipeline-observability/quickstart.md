# Quickstart: Validação da Observabilidade de Pipeline

Este guia descreve os procedimentos para validar de ponta a ponta a observabilidade de execuções do pipeline, a compatibilidade `run_id == release_id`, a proteção RBAC para administradores e a renderização dinâmica e minimalista de etapas na interface de validação.

---

## 1. Pré-Requisitos

Certifique-se de que as dependências e o ambiente estejam configurados:

```bash
# Ativar ambiente Poetry e verificar lint
poetry run ruff check

# Garantir que o diretório de armazenamento de execuções exista
mkdir -p lumina/storage/pipeline_runs
```

---

## 2. Testes Automatizados (Pytest)

A suíte de testes valida isolamento de acesso, gravação de eventos JSONL, consolidação dinâmica de etapas e ausência de vazamento de dados pessoais (LGPD).

```bash
# Executar todos os testes da feature (sem gastar tokens de IA)
poetry run pytest tests/api/routers/test_processing_runs.py tests/unit/services/test_run_logger.py -v

# Executar a suíte completa padrão do projeto
poetry run task test
```

### O que os testes cobrem:
- **Segurança (RBAC)**: Usuário comum recebe `403 Forbidden` em `GET /processing-runs`; usuário não autenticado recebe `401 Unauthorized`; administrador recebe `200 OK`.
- **Compatibilidade `run_id == release_id`**: O `run_id` gerado durante a execução do release é rigorosamente igual ao `release_id`.
- **Dinamismo de Etapas**: Adicionar um evento com um nome de etapa inédito (ex: `'table_extraction'`) resulta na etapa aparecendo na lista `stages` com status e duração calculados.
- **Proteção LGPD**: Dados pessoais não anonimizados nunca constam nas linhas do arquivo `.jsonl`.

---

## 3. Validação via API (cURL)

### 3.1 Obter Token de Administrador
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/sign-in \
  -F "username=admin" \
  -F "password=admin_password" | jq -r .access_token)
```

### 3.2 Listar Execuções de Pipeline
```bash
curl -s -X GET "http://localhost:8000/processing-runs?limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### 3.3 Obter Detalhe de uma Execução Específica pelo `release_id`
```bash
RELEASE_ID="3fa85f64-5717-4562-b3fc-2c963f66afa6"

curl -s -X GET "http://localhost:8000/processing-runs/$RELEASE_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

## 4. Validação Visual Interativa (Página HTML de Demonstração)

Em conformidade com o Princípio VII da Constituição, a funcionalidade disponibiliza uma interface HTML simples, direta e autocontida:

1. **Iniciar a aplicação FastAPI**:
   ```bash
   poetry run task run
   ```

2. **Acessar a página de validação no navegador**:
   Abra: `http://localhost:8000/demos/pipeline_observability/`

3. **Passo a passo de verificação na interface**:
   - **Autenticação**: Selecione a persona "Administrador" (ou insira o token JWT de admin).
   - **Listagem de Releases**: A tabela exibirá as releases recentes com ID da Release (`release_id`), Documento, Status (`SUCCESS` / `FAILED` / `IN_PROGRESS`), Tempo Total formatado (ex: `1m42s`) e Data.
   - **Busca Rápida**: Digite ou cole o `release_id` no campo de busca para filtrar diretamente a execução.
   - **Inspeção das 7 Macroetapas**: Clique na linha da release para expandir o detalhamento. Observe as macroetapas consolidadas da ingestão e da release sequencialmente (ex: `✓ Extração`, `✓ Identificação de Seções`, `✓ Anonimização LGPD`, `✓ Embeddings`, `✓ Avaliação Estruturada`, `✓ Resolução de Coordenadas`, `✓ Síntese Executiva`).
   - **Navegação em Sub-Abas [Entrada | Estado Interno | Saída]**: Em cada etapa, alterne entre as abas para verificar variáveis de entrada (janelas de texto, queries triplicadas), estado interno (chunks intermediários, taxas de mapeamento) e saídas (scores, citações, parecer estruturado).
   - **Diagnóstico de Critérios Concorrentes**: Na etapa de "Avaliação", inspecione a tabela de critérios individuais com seus tempos em lote, notas, citações e detecção de alucinações.
   - **Cópia Rápida de Prompts**: Em modo debug (`DEBUG_PIPELINE_RUNS=true`), visualize a cópia integral do prompt e da resposta bruta da LLM com o botão de cópia rápida.
   - **Tentativa de Acesso com Não-Admin**: Troque a persona para "Aluno / Pesquisador" e tente carregar as execuções; confirme o alerta visual de acesso negado (`403 Forbidden`).

---

## 5. Catálogo Central de Demos

Abra `http://localhost:8000/demos/` e certifique-se de que o card "Observabilidade de Pipeline (Spec 002)" está listado e navegável.
