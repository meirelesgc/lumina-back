from http import HTTPStatus

import pytest
from fastapi.routing import APIRoute, APIWebSocketRoute

from lumina.app import app
from lumina.core.security import get_current_user, get_current_ws_user

PUBLIC_ROUTES = {
    ('GET', '/health'),
    ('POST', '/auth/token'),
    ('POST', '/auth/sign-in'),
    ('POST', '/auth/forgot-password'),
    ('POST', '/auth/reset-password'),
    ('POST', '/user'),
    ('POST', '/user/forgot-password'),
    ('POST', '/user/reset-password'),
    ('GET', '/invitations/{token}'),
    ('POST', '/invitations/{token}/register'),
    ('POST', '/invitations/{token}/reject'),
}


def depends_on_session(dependant) -> bool:
    return any(
        dep.call in {get_current_user, get_current_ws_user}
        or depends_on_session(dep)
        for dep in dependant.dependencies
    )


def api_routes():
    for route in app.routes:
        if isinstance(route, APIRoute):
            for method in route.methods:
                yield method, route.path, route
        elif isinstance(route, APIWebSocketRoute):
            yield 'WEBSOCKET', route.path, route


def test_toda_rota_fora_da_lista_publica_exige_sessao():
    open_routes = sorted(
        (method, path)
        for method, path, route in api_routes()
        if (method, path) not in PUBLIC_ROUTES
        and not depends_on_session(route.dependant)
    )
    assert open_routes == []


def test_lista_publica_nao_tem_rota_inexistente():
    known = {(method, path) for method, path, _ in api_routes()}
    assert PUBLIC_ROUTES <= known


@pytest.mark.parametrize(
    'path',
    [
        '/typification',
        '/document-group',
        '/stats/kpis',
        '/export/typifications/pdf',
        '/uploads/qualquer.pdf',
    ],
)
def test_visitante_recebe_401(client, path):
    assert client.get(path).status_code == HTTPStatus.UNAUTHORIZED
