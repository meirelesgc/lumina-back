from http import HTTPStatus


def test_create_project_api(client, token):
    headers = {'Authorization': f'Bearer {token}'}
    payload = {'name': 'API Test Project', 'description': 'Created via API'}

    response = client.post('/project', json=payload, headers=headers)
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['name'] == 'API Test Project'

    # Try to create again to trigger conflict
    response2 = client.post('/project', json=payload, headers=headers)
    assert response2.status_code == HTTPStatus.CONFLICT


def test_get_projects_api(client, token):
    headers = {'Authorization': f'Bearer {token}'}

    # First create a project
    client.post('/project', json={'name': 'API Project 1'}, headers=headers)

    response = client.get('/project', headers=headers)
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert 'projects' in data
    assert len(data['projects']) > 0


def test_update_project_api(client, token):
    headers = {'Authorization': f'Bearer {token}'}

    # Create project
    create_res = client.post(
        '/project', json={'name': 'To Update Project'}, headers=headers
    )
    project_id = create_res.json()['id']

    # Update project
    update_payload = {
        'id': project_id,
        'name': 'Updated Project API',
        'status': 'FINALIZADO',
    }
    update_res = client.put('/project', json=update_payload, headers=headers)
    assert update_res.status_code == HTTPStatus.OK
    assert update_res.json()['name'] == 'Updated Project API'


def test_delete_project_api(client, token):
    headers = {'Authorization': f'Bearer {token}'}

    # Create project
    create_res = client.post(
        '/project', json={'name': 'To Delete Project'}, headers=headers
    )
    project_id = create_res.json()['id']

    # Delete project
    del_res = client.delete(f'/project/{project_id}', headers=headers)
    assert del_res.status_code == HTTPStatus.NO_CONTENT

    # Verify deleted
    get_res = client.get(f'/project/{project_id}', headers=headers)
    assert get_res.status_code == HTTPStatus.NOT_FOUND
