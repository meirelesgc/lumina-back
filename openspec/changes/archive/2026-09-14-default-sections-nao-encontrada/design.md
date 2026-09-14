## Context

Atualmente, `lumina/services/ai/stages/sections.py` executa chamadas consecutivas à LLM utilizando janelas textuais de 3.000 caracteres para identificar macro-seções e, em seguida, faz alinhamento de strings com `normalize_with_mapping` e `find_valid_sections`. Conforme estabelecido no `proposal.md`, essa detecção por LLM será removida e substituída por uma atribuição padrão determinística ("NÃO ENCONTRADA") até que um novo método seja introduzido.

O pipeline em `lumina/services/ai/pipeline.py` consome essa etapa através de duas funções com telemetria:
- `assign_sections_with_telemetry(chunks, model, run_id)` para PDFs.
- `split_sections_with_telemetry(raw_docs, model, run_id)` para DOCX/TXT.

## Goals / Non-Goals

**Goals:**
- Eliminar completamente as chamadas de IA/LLM, particionamento de janelas e reconciliação difusa no módulo `sections.py`.
- Definir `DEFAULT_SECTION_TITLE = 'NÃO ENCONTRADA'`.
- Garantir que todos os chunks de PDFs recebam `chunk.metadata['section_title'] = DEFAULT_SECTION_TITLE` e o prefixo `SECTION: NÃO ENCONTRADA\n\n{conteudo}`.
- Garantir que os documentos de texto (DOCX/TXT) recebam `doc.metadata['section_title'] = DEFAULT_SECTION_TITLE`.
- Preservar o registro no `RunLogger` com metadados estruturados limpos (`sections_detected: []`, `mapping_success_rate: 1.0`).
- Manter compatibilidade com `stages/__init__.py` e `pipeline.py`.
- Adicionar testes unitários dedicados cobrindo o comportamento padrão ("NÃO ENCONTRADA").

**Non-Goals:**
- Implementar a nova estratégia definitiva de identificação de seções (será realizada em mudança posterior).
- Alterar o pipeline de busca semântica em `retrieval.py` ou a estrutura do banco de dados vetorial.
- Modificar os contratos públicos das rotas da API.

## Decisions

### 1. Constante de Seção Padrão
- **Decisão**: Centralizar a constante `DEFAULT_SECTION_TITLE: str = 'NÃO ENCONTRADA'` em `lumina/services/ai/stages/sections.py`.
- **Racional**: Evita strings mágicas espalhadas e facilita a substituição futura quando o novo método for implementado.

### 2. Simplificação de `assign_sections_to_chunks` e `split_by_sections`
- **Decisão**: 
  - `assign_sections_to_chunks(chunks, model=None)`: Itera diretamente sobre `chunks`, atualiza o metadado `section_title` para `DEFAULT_SECTION_TITLE` e adiciona o prefixo `SECTION: NÃO ENCONTRADA\n\n` ao `page_content`. Retorna `(chunks, sections_meta)`.
  - `split_by_sections(documents, model=None)`: Atualiza `doc.metadata['section_title'] = DEFAULT_SECTION_TITLE` para cada documento em `documents`. Retorna `(documents, sections_meta)`.
- **Alternativa considerada**: Retornar `None` ou string vazia. *Descartada* porque a solicitação do usuário exige explicitamente o retorno `"NÃO ENCONTRADA"`, além de manter compatibilidade com o retriever que espera um título de seção.

### 3. Remoção de Chamadas à LLM e Preservação de Assinaturas
- **Decisão**: Remover a dependência de `structured_model.invoke(prompt)` e o loop de 3.000 caracteres de `detect_sections_with_model`. As funções continuam aceitando o parâmetro `model` como opcional (`Optional[BaseChatModel] = None`) para manter compatibilidade com as chamadas em `pipeline.py` sem quebrar interfaces.
- **Racional**: `pipeline.py` passa `model` ao chamar `assign_sections_with_telemetry` e `split_sections_with_telemetry`. Manter o argumento na assinatura evita alterações desnecessárias no orquestrador do pipeline.

### 4. Telemetria Neutra no RunLogger
- **Decisão**: O `sections_meta` emitido será:
  ```python
  {
      'input_window_text': '',
      'sections_detected': [],
      'mapping_success_rate': 1.0,
      'default_assigned': DEFAULT_SECTION_TITLE,
  }
  ```
- **Racional**: Não quebra a serialização de eventos do `RunLogger` e registra adequadamente que 0 seções complexas foram identificadas via modelo.

## Risks / Trade-offs

- **[Risk] Impacto na relevância da busca vetorial (RAG)**: Chunks terão `SECTION: NÃO ENCONTRADA`, enquanto a busca por critério triplica o nome da taxonomia esperada (ex: `SECTION: Metodologia`).
  - *Mitigação*: Este é o comportamento esperado de um fallback/stub temporário enquanto a nova detecção não é implementada. Como a busca usa embeddings de texto completo, os chunks ainda serão recuperados pelo conteúdo restante da query e expansão de margem ($\pm 2$).
