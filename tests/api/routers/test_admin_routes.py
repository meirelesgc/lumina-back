from http import HTTPStatus

import pytest

ID = '00000000-0000-0000-0000-000000000001'

ADMIN_ROUTES = [
    ('POST', '/typification'),
    ('PUT', '/typification'),
    ('DELETE', f'/typification/{ID}'),
    ('POST', '/taxonomy'),
    ('PUT', '/taxonomy'),
    ('DELETE', f'/taxonomy/{ID}'),
    ('POST', '/branch'),
    ('PUT', '/branch'),
    ('DELETE', f'/branch/{ID}'),
    ('POST', '/source'),
    ('POST', f'/source/{ID}/upload'),
    ('PUT', '/source'),
    ('DELETE', f'/source/{ID}'),
    ('POST', '/document-group'),
    ('PUT', '/document-group'),
    ('DELETE', f'/document-group/{ID}'),
    ('POST', f'/document-group/{ID}/item'),
    ('PUT', f'/document-group/{ID}/items/order'),
    ('PUT', '/document-group/item'),
    ('DELETE', f'/document-group/item/{ID}'),
    ('POST', f'/document-group/item/{ID}/attachment'),
    ('PUT', f'/document-group/item/{ID}/attachments/order'),
    ('PUT', '/document-group/attachment'),
    ('DELETE', f'/document-group/attachment/{ID}'),
    ('POST', '/tree-suggestion'),
    ('GET', '/tree-suggestion'),
    ('GET', f'/tree-suggestion/{ID}'),
    ('POST', f'/tree-suggestion/{ID}/items/{ID}/confirm'),
    ('POST', f'/tree-suggestion/{ID}/items/{ID}/discard'),
    ('POST', f'/tree-suggestion/{ID}/discard'),
    ('POST', '/templates'),
    ('PUT', f'/templates/{ID}'),
    ('DELETE', f'/templates/{ID}'),
    ('GET', '/stats/kpis'),
    ('GET', '/stats/most-used-typifications'),
    ('GET', '/stats/user-message-activity'),
    ('POST', '/system-settings'),
    ('GET', '/system-settings'),
    ('PUT', '/system-settings/chave'),
    ('DELETE', '/system-settings/chave'),
    ('GET', '/system-settings/chave'),
]


@pytest.mark.parametrize(('method', 'path'), ADMIN_ROUTES)
def test_usuario_comum_recebe_403(client, token, method, path):
    response = client.request(
        method, path, headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.FORBIDDEN, response.text


@pytest.mark.parametrize(
    'path', ['/document-group', '/typification', '/templates']
)
def test_usuario_comum_le_o_configurador(client, token, path):
    response = client.get(path, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == HTTPStatus.OK


def test_admin_cria_tipificacao(client, admin_token):
    response = client.post(
        '/typification',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'name': 'Edital', 'source_ids': []},
    )
    assert response.status_code == HTTPStatus.CREATED, response.text
