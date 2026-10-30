"""
Jornada: o analista envia uma revisão sistemática e avalia um ramo que
menciona "Revisão Sistemática". Ele espera receber trechos com conteúdo do
documento, e não os chunks que só repetem o título corrido do cabeçalho.
A recuperação só enxerga o texto que virou chunk, então estes testes
verificam a extração contra os gabaritos `<nome>.running.yaml` de
`tests/fixtures/documents/` (OpenSpec: strip-running-headers-footers).

Os dois testes são críticos, com tolerância zero por documento:
- linha corrida nos chunks ocupa vagas de trechos sem trazer conteúdo;
- linha que o gabarito manda manter, como uma legenda de figura, é texto
  do documento que o usuário não recupera depois.
"""

import pytest

from tests.fixtures.answer_keys import (
    RUNNING_KEYS,
    doc_id,
    expected_keep_lines,
    expected_running_lines,
    extract,
    letters_and_digits,
    page_texts,
    pdf_for,
)


@pytest.mark.parametrize('answer_key', RUNNING_KEYS, ids=doc_id)
def test_linhas_corridas_nao_chegam_aos_chunks(answer_key):
    pages = page_texts(extract(pdf_for(answer_key)))

    leaked = {}
    for line in expected_running_lines(answer_key):
        text = letters_and_digits(line['text'])
        keep = set(line.get('keep_on_pages', []))
        found = sorted(
            page
            for page, page_text in pages.items()
            if page not in keep and text in page_text
        )
        if found:
            leaked[line['text']] = found

    assert not leaked, f'Linhas corridas nos chunks (páginas): {leaked}'


@pytest.mark.parametrize('answer_key', RUNNING_KEYS, ids=doc_id)
def test_linhas_a_manter_continuam_nos_chunks(answer_key):
    pages = page_texts(extract(pdf_for(answer_key)))

    missing = [
        f'{line["text"]} (página {line["page"]})'
        for line in expected_keep_lines(answer_key)
        if letters_and_digits(line['text']) not in pages.get(line['page'], '')
    ]

    assert not missing, f'Linhas a manter fora dos chunks: {missing}'
