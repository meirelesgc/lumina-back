from lumina.utils.pii import sanitize_pii


def test_sanitize_pii_masks_documents_and_contacts():
    text = (
        'CPF: 12345678901, CNPJ: 12.345.678/0001-90, Tel: 2199888-7766, '
        'E-mail: usuario@dominio.com.br'
    )
    sanitized = sanitize_pii(text)
    assert '12345678901' not in sanitized
    assert '12.345.678/0001-90' not in sanitized
    assert '[CPF_MASKED]' in sanitized
    assert '[CNPJ_MASKED]' in sanitized
    assert '[EMAIL_MASKED]' in sanitized


def test_sanitize_pii_preserves_uuids():
    run_id = '9b65eec5-dd3b-45a5-b13c-cdf16cd0fedb'
    assert sanitize_pii(f'Falha na sessão {run_id}') == (
        f'Falha na sessão {run_id}'
    )
