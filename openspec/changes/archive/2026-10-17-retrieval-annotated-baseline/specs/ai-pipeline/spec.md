## ADDED Requirements

### Requirement: Critério de Aceite da Recuperação sobre Acervo Anotado
O sistema SHALL ter a recuperação de evidências validada contra um acervo versionado de PDFs. Cada PDF anotado SHALL ter um gabarito que reúne a árvore de critérios a avaliar e, para cada critério, os trechos esperados entre as evidências, com página, um trecho do texto do documento e, quando o trecho pertence a uma seção anotada, a seção. A validação SHALL usar o mesmo caminho de ingestão e de recuperação de uma avaliação real, com os mesmos embeddings. As métricas SHALL somar os resultados de todo o acervo e falhar abaixo de um piso registrado, que só sobe.

#### Scenario: Trecho anotado inexistente no documento indexado
- **WHEN** um trecho do gabarito não aparece no texto anonimizado dos chunks da página anotada e, quando o gabarito informa a seção, dessa seção
- **THEN** a validação do gabarito falha sem chamar modelos e aponta o documento, o critério e o trecho

#### Scenario: Seção anotada fora do gabarito de seções
- **WHEN** um trecho do gabarito cita uma seção que não está no gabarito de seções do mesmo documento
- **THEN** a validação do gabarito falha e aponta o documento, o critério e a seção

#### Scenario: Trecho fora das seções anotadas
- **WHEN** um trecho do gabarito não informa seção, como o título na capa
- **THEN** a validação do gabarito confere só a página, e o acerto de seção e página desse trecho depende só da página

#### Scenario: Evidência de outro documento
- **WHEN** a recuperação devolve, para um critério, uma evidência indexada a partir de outro documento do acervo
- **THEN** a validação falha e aponta o documento e o critério

#### Scenario: Métrica de recuperação abaixo do piso
- **WHEN** o recall de trechos, o acerto de seção e página, a precisão entre critérios ou o acerto do roteamento por seção, somados sobre o acervo, ficam abaixo do piso registrado da métrica
- **THEN** a validação falha e informa o placar por documento e por critério

#### Scenario: Métricas de recuperação no piso ou acima
- **WHEN** todas as métricas atingem os pisos registrados
- **THEN** a validação passa e informa o placar por documento e por critério, mesmo com trechos individuais não recuperados

#### Scenario: Critério sem evidência no documento
- **WHEN** o gabarito declara que o documento não atende um critério
- **THEN** a validação informa o que a recuperação devolveu para ele e o resultado do roteamento, sem contar o critério nas métricas com piso
