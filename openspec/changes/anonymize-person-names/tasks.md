## 1. Gabarito de nomes

- [ ] 1.1 Acrescentar `person_names` aos quatro `<nome>.sections.yaml` do acervo com os nomes de autoria de cada documento (capa, folha de rosto, cabeçalho de artigo, orientador), copiados do PDF. Documentar o campo em `tests/fixtures/documents/section_template.yaml` e no README do acervo. O usuário revisa o diff das listas antes do commit. Verificar que `poetry run pytest tests/unit/services/test_ingestion_sections.py -s` passa com o mesmo placar de antes.
- [ ] 1.2 Em `tests/fixtures/answer_keys.py`, ler `person_names` do gabarito de seções. Verificar pelo teste da tarefa 2.1.

## 2. Testes

- [ ] 2.1 Criar `tests/unit/services/test_anonymization_corpus.py`, parametrizado pelos `*.sections.yaml`: nenhum nome de `person_names`, comparado com `normalize`, aparece em `page_content`, `section_title` ou `section_path` dos chunks de `anonymized(pdf)`. A mensagem aponta documento, `chunk_id`, campo e nome. Verificar que o teste falha antes da mudança nos quatro documentos, inclusive em `chunk_0_0` e `chunk_1_0` do anteprojeto.
- [ ] 2.2 Em `tests/unit/services/test_metadata_anonymization.py`, criar os testes focados, todos chamando `anonymize_chunks` com chunks montados no teste:
  - nome em maiúsculas em `page_content`, `section_title` e `section_path` vira `<PERSON_0>`;
  - o mesmo nome em maiúsculas e em caixa de título recebe um só marcador, e `presidio_mapping['PERSON']` tem uma só entrada;
  - nome coletado no corpo é mascarado num chunk de papel `references`;
  - autor que só aparece num chunk `references` continua no texto;
  - sobrenome isolado de citação ("Laubheimer (2020)") continua no texto;
  - expressão capitalizada cujas palavras aparecem em minúsculas em outro chunk ("Energias Renováveis") continua no texto;
  - expressão igual a um título de seção continua no texto.

  Verificar que os testes de nome falham antes da mudança. Os de "continua no texto" passam desde o início como guardas, e a tarefa registra isso.

## 3. Implementação

- [ ] 3.1 Em `lumina/utils/InstanceCounterAnonymizer.py`, procurar o texto no mapa sem distinção de caixa antes de criar um índice novo, sem gravar a nova forma. Verificar pelo teste de marcador único da tarefa 2.2 e que `test_metadata_anonymization_cpf_and_names` continua passando.
- [ ] 3.2 Em `lumina/utils/PresidioAnonymizer.py`, implementar a coleta (normalização das sequências em maiúsculas, spans `PER` do `analyzer.nlp_engine`, chunks fora de `references`) e o filtro das quatro regras do design. Verificar pelos testes de guarda da tarefa 2.2.
- [ ] 3.3 Em `PresidioAnonymizer.anonymize_chunks`, registrar o `PatternRecognizer` de `PERSON` com os nomes coletados antes do mascaramento e removê-lo ao final. Verificar que os testes das tarefas 2.1 e 2.2 passam.

## 4. Documentação

- [ ] 4.1 Atualizar "Anonimização com Microsoft Presidio" em `docs/ia-plataforma.md` com as duas passadas, o filtro e o marcador `<PERSON_n>`, e citar o teste do acervo em "Validação da Ingestão sobre Acervo Anotado" de `docs/arquitetura-engenharia.md`. Verificar que os nomes de arquivos e funções citados existem no código.

## 5. Verificação

- [ ] 5.1 Rodar `poetry run task test`, `ruff check` e `ruff format --check` nos arquivos alterados, e registrar aqui o resultado. Confirmar que `test_retrieval_answer_keys.py` passa sem mudança nos `*.retrieval.yaml`, e registrar o tempo de `test_ingestion_sections.py` antes e depois.
- [ ] 5.2 Rodar `poetry run pytest tests/ai/evaluation/retrieval -s --run-ai -m ai` e registrar aqui o placar. Se uma métrica cair abaixo do piso, parar e trazer o placar ao usuário antes de mexer no piso.

## Workflow follow-up

- Abrir a issue da árvore de seções que usa o nome da capa como título e citar o número em `proposal.md` e `design.md`.
- Commitar estes artefatos em `docs(openspec): ...`, separados do código e dos testes.
- Arquivar a change depois da revisão e fechar a issue #22.
