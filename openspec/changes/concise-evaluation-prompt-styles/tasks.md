## 1. Prompts

- [x] 1.1 Reescrever `DOCUMENT_ANALYSIS_PROMPT` em `lumina/prompts.py` como base fixa objetiva
      (barema, fidelidade aos trechos, citações, política de sugestões, limites de tamanho,
      placeholder `{style_instructions}`), sem persona extensa nem emojis
- [x] 1.2 Criar `EVALUATION_STYLES` (`verdict_lists`, `checklist`, `table`, `summary_bullets`)
      em `lumina/prompts.py`
- [x] 1.3 Reescrever `DESCRIPTION` com saudação de uma frase, listas curtas, títulos de seção
      fixos e placeholder `{style_instructions}`
- [x] 1.4 Criar `SYNTHESIS_STYLES` (`bullets`, `checklist`, `summary_bullets`) em
      `lumina/prompts.py`
- [x] 1.5 Atualizar a descrição do campo `feedback` em `DocumentReleaseFeedback`
      (`lumina/schemas/document_release.py`)

## 2. Avaliação por critério

- [x] 2.1 Criar `select_evaluation_style` e sortear `style_instructions` por item antes do laço
      de retentativas em `evaluate_criteria_batch` (`lumina/services/ai/stages/evaluation.py`)
- [x] 2.2 Declarar `style_instructions` em `input_variables` de `get_evaluation_chain`
- [x] 2.3 Criar helper de `verbosity="low"` (via `model_copy`, só quando o modelo declara o
      campo) e aplicá-lo em `get_evaluation_chain`

## 3. Síntese executiva

- [x] 3.1 Sortear estilo de `SYNTHESIS_STYLES` em `generate_synthesis_prompt`
      (`lumina/services/ai/stages/synthesis.py`)
- [x] 3.2 Apresentar os pareceres de entrada como bloco indentado sob cada critério
- [x] 3.3 Aplicar `verbosity="low"` em `record_synthesis_stage`

## 4. Testes e validação

- [x] 4.1 Testes de sorteio: cada critério recebe um estilo de `EVALUATION_STYLES`; o estilo se
      mantém nas retentativas; o prompt renderizado contém o bloco de estilo
- [x] 4.2 Testes da síntese: o prompt contém os três títulos fixos e o bloco de estilo sorteado
      para cada estilo; pareceres de várias linhas aparecem indentados
- [x] 4.3 Testes do helper de verbosity: aplica em `ChatOpenAI` sem alterar o modelo original;
      devolve inalterado um modelo sem o campo
- [x] 4.4 Executar `poetry run ruff check` e `poetry run task test` e confirmar suíte completa
      passando

## 5. Documentação

- [ ] 5.1 Atualizar `docs/ia-plataforma.md` (seção 4: regras de avaliação, schema e síntese)
      com o formato curto, a política de sugestões e os estilos sorteados
