## 1. Gabarito de nomes

- [x] 1.1 Acrescentar `person_names` aos quatro `<nome>.sections.yaml` do acervo com os nomes de autoria de cada documento (capa, folha de rosto, cabeçalho de artigo, orientador), copiados do PDF. Documentar o campo em `tests/fixtures/documents/section_template.yaml` e no README do acervo. O usuário revisa o diff das listas antes do commit. Verificar que `poetry run pytest tests/unit/services/test_ingestion_sections.py -s` passa com o mesmo placar de antes.
  - Resultado: 25 nomes (anteprojeto 2, artigo 5, dengue 8, microgrids 8 autores e 2 editores acadêmicos). O usuário revisou as listas. Placar de seções 63/63, o mesmo de antes.
- [x] 1.2 Em `tests/fixtures/answer_keys.py`, ler `person_names` do gabarito de seções. Verificar pelo teste da tarefa 2.1.

## 2. Testes

- [x] 2.1 Criar `tests/unit/services/test_anonymization_corpus.py`, parametrizado pelos `*.sections.yaml`: nenhum nome de `person_names`, comparado com `normalize`, aparece em `page_content`, `section_title` ou `section_path` dos chunks de `anonymized(pdf)`. A mensagem aponta documento, `chunk_id`, campo e nome. Verificar que o teste falha antes da mudança nos quatro documentos, inclusive em `chunk_0_0` e `chunk_1_0` do anteprojeto.
  - Resultado: antes da mudança, o teste falhou nos quatro documentos. No anteprojeto, o nome da autora apareceu em `page_content`, `section_title` e `section_path` de `chunk_0_0` e `chunk_1_0`. Depois da mudança, passa nos quatro.
- [x] 2.2 Em `tests/unit/services/test_metadata_anonymization.py`, criar os testes focados, todos chamando `anonymize_chunks` com chunks montados no teste:
  - nome em maiúsculas em `page_content`, `section_title` e `section_path` vira `<PERSON_0>`;
  - o mesmo nome em maiúsculas e em caixa de título recebe um só marcador, e `presidio_mapping['PERSON']` tem uma só entrada;
  - nome coletado no corpo é mascarado num chunk de papel `references`;
  - autor que só aparece num chunk `references` continua no texto;
  - sobrenome isolado de citação ("Laubheimer (2020)") continua no texto;
  - expressão capitalizada cujas palavras aparecem em minúsculas em outro chunk ("Energias Renováveis") continua no texto;
  - expressão igual a um título numerado de seção continua no texto.

  Verificar que os testes de nome falham antes da mudança. Os de "continua no texto" passam desde o início como guardas, e a tarefa registra isso.
  - Resultado: os 3 testes de nome falharam antes da mudança, e as 4 guardas passaram. Para provar que as guardas testam o filtro, cada regra foi desligada na implementação e a guarda correspondente falhou. A guarda do título numerado usa o texto do `chunk_6_3` do artigo, porque o spaCy não marca a expressão num texto inventado.

## 3. Implementação

- [x] 3.1 Em `lumina/utils/InstanceCounterAnonymizer.py`, procurar o texto no mapa sem distinção de caixa antes de criar um índice novo, sem gravar a nova forma. Verificar pelo teste de marcador único da tarefa 2.2 e que `test_metadata_anonymization_cpf_and_names` continua passando.
- [x] 3.2 Em `lumina/utils/PresidioAnonymizer.py`, implementar a coleta (normalização das sequências em maiúsculas, spans `PER` do `analyzer.nlp_engine`, chunks fora de `references`) e o filtro das quatro regras do design. Verificar pelos testes de guarda da tarefa 2.2.
- [x] 3.3 Em `PresidioAnonymizer.anonymize_chunks`, registrar o `PatternRecognizer` de `PERSON` com os nomes coletados antes do mascaramento e removê-lo ao final. Verificar que os testes das tarefas 2.1 e 2.2 passam.

## 4. Documentação

- [x] 4.1 Atualizar "Anonimização com Microsoft Presidio" em `docs/ia-plataforma.md` com as duas passadas, o filtro e o marcador `<PERSON_n>`, e citar o teste do acervo em "Validação da Ingestão sobre Acervo Anotado" de `docs/arquitetura-engenharia.md`. Verificar que os nomes de arquivos e funções citados existem no código.

## 5. Verificação

- [x] 5.1 Rodar `poetry run task test`, `ruff check` e `ruff format --check` nos arquivos alterados, e registrar aqui o resultado. Confirmar que `test_retrieval_answer_keys.py` passa sem mudança nos `*.retrieval.yaml`, e registrar o tempo de `test_ingestion_sections.py` antes e depois.
  - Resultado: 511 testes passam e 12 são pulados (os de `@pytest.mark.ai`), com 80% de cobertura de `lumina/`. `test_retrieval_answer_keys.py` passa sem mudança nos `*.retrieval.yaml`. `ruff format --check` passa nos cinco arquivos Python alterados. `ruff check` acusa em `PresidioAnonymizer.py` os mesmos 5 avisos que o arquivo já tinha na `main` (`_setup_analyzer` e docstrings), e nenhum nas linhas novas.
  - Tempo: `test_ingestion_sections.py` não chama a anonimização, então a medida foi feita direto sobre `anonymize_chunks` nos quatro PDFs: 27,4 s antes e 27,4 s depois. A carga do modelo spaCy, que já existia, domina o tempo.
  - A suíte roda com `DOCKER_HOST=unix:///home/gls/.docker/desktop/docker.sock` quando só o Docker Desktop está ativo.
- [x] 5.2 Rodar `poetry run pytest tests/ai/evaluation/retrieval -s --run-ai -m ai` e registrar aqui o placar. Se uma métrica cair abaixo do piso, parar e trazer o placar ao usuário antes de mexer no piso.
  - Resultado: o acerto de seção e página caiu para 74/129, abaixo do piso de 0,58. O usuário decidiu baixar `MIN_SECTION_PAGE_HIT_RATE` para 0.57. Com o piso novo, os 4 testes de `test_retrieval_baseline.py` passam.

    | Métrica | `main` | Esta mudança | Piso |
    | :--- | ---: | ---: | ---: |
    | Recall de trechos | 69/129 = 0,53 | 69/129 = 0,53 | 0,53 |
    | Seção e página | 75/129 = 0,58 | 74/129 = 0,57 | 0,58 para 0,57 |
    | Precisão entre ramos | 40/202 = 0,20 | 40/196 = 0,20 | 0,19 |
    | Roteamento | 0/64 | 0/64 | 0,0 |

    Justificativa da queda do piso: a anonimização muda de propósito o texto dos chunks com nomes, e os embeddings mudam junto. Em `pesquisas-futuras` do microgrids, "Abstract" tomou de "5. Conclusions" o 5º lugar do ranking. A `main` já estava exatamente no piso. Em `desfechos-definidos` da dengue, o trecho entrou no ranking, sem acerto de seção e página.

    O código final rodou três vezes. A primeira rodou `tests/ai/evaluation/retrieval` inteiro: `test_outline_selection.py` passou, e só o piso de seção e página falhou, com o placar perdido na saída cortada. As duas seguintes rodaram só `test_retrieval_baseline.py` e deram 74/129. A precisão variou de 40/197 para 40/196 entre elas.

## Workflow follow-up

- Commitar estes artefatos em `docs(openspec): ...`, separados do código e dos testes.
- Arquivar a change depois da revisão e fechar a issue #22.
