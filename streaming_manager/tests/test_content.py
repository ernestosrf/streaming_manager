from src.models.content import Content
from src.models.db import db
from tests.conftest import add_content, add_platform, auth_header, create_admin, create_user


def test_home_watchlist_is_admin_catalog(client, app):
    admin = create_admin()
    other = create_user('maria', 'senha1234')
    add_content(admin, title='Filme Admin')
    add_content(other, title='Filme Maria')

    response = client.get('/api/watchlists')
    assert response.status_code == 200
    data = response.get_json()
    titles = [item['title'] for item in data['contents']]
    assert titles == ['Filme Admin']
    assert data['owner']['username'] == 'admin'


def test_user_watchlist_is_public_and_independent(client, app):
    admin = create_admin()
    maria = create_user('maria', 'senha1234')
    add_content(admin, title='Filme Admin')
    add_content(maria, title='Filme Maria')

    response = client.get('/api/watchlists/maria')
    assert response.status_code == 200
    titles = [item['title'] for item in response.get_json()['contents']]
    assert titles == ['Filme Maria']


def test_meta_exposes_admin_username(client, app):
    create_admin()
    response = client.get('/api/meta')
    assert response.status_code == 200
    assert response.get_json()['admin_username'] == 'admin'


def test_inactive_account_watchlist_is_unavailable(client, app):
    from src.models.user import STATUS_INACTIVE
    create_admin()
    maria = create_user('maria', 'senha1234', status=STATUS_INACTIVE)
    add_content(maria, title='Escondido')
    response = client.get('/api/watchlists/maria')
    assert response.status_code == 404


def test_user_cannot_edit_another_watchlist(client, app):
    admin = create_admin()
    maria = create_user('maria', 'senha1234')
    joao = create_user('joao', 'senha1234')
    content = add_content(maria, title='So Maria')
    headers = auth_header(client, 'joao', 'senha1234')

    update = client.put(f'/api/content/{content.id}', json={'title': 'Hack'}, headers=headers)
    assert update.status_code == 403

    admin_headers = auth_header(client, 'admin', 'admin-password')
    admin_update = client.put(f'/api/content/{content.id}', json={'title': 'Admin edit'}, headers=admin_headers)
    assert admin_update.status_code == 403


def test_owner_can_create_edit_toggle_and_delete(client, app):
    create_admin()
    maria = create_user('maria', 'senha1234')
    platform = add_platform()
    headers = auth_header(client, 'maria', 'senha1234')

    created = client.post('/api/content', json={
        'title': 'Interestelar',
        'year': 2014,
        'type': 'movie',
        'genre': 'Ficção',
        'poster_url': 'http://example.com/i.jpg',
        'streaming_ids': [platform.id],
    }, headers=headers)
    assert created.status_code == 201
    content_id = created.get_json()['id']

    updated = client.put(f'/api/content/{content_id}', json={'title': 'Interstellar'}, headers=headers)
    assert updated.status_code == 200
    assert updated.get_json()['title'] == 'Interstellar'

    toggled = client.patch(f'/api/content/{content_id}/toggle', headers=headers)
    assert toggled.status_code == 200
    assert toggled.get_json()['is_active'] is False

    public = client.get('/api/watchlists/maria')
    assert public.get_json()['contents'] == []

    owner_view = client.get('/api/watchlists/maria?show_inactive=true', headers=headers)
    assert len(owner_view.get_json()['contents']) == 1

    deleted = client.delete(f'/api/content/{content_id}', headers=headers)
    assert deleted.status_code == 200


def test_suggestions_copy_is_independent(client, app):
    admin = create_admin()
    maria = create_user('maria', 'senha1234')
    platform = add_platform()
    original = add_content(admin, title='Matrix', year=1999, streamings=[platform])
    headers = auth_header(client, 'maria', 'senha1234')

    suggestions = client.get('/api/content/suggestions?q=mat', headers=headers)
    assert suggestions.status_code == 200
    payload = suggestions.get_json()
    assert payload[0]['title'] == 'Matrix'
    assert 'owner' not in payload[0]

    copied = client.post('/api/content', json={
        'title': payload[0]['title'],
        'year': payload[0]['year'],
        'type': payload[0]['type'],
        'genre': payload[0]['genre'],
        'poster_url': payload[0]['poster_url'],
        'streaming_ids': [platform.id],
    }, headers=headers)
    assert copied.status_code == 201
    copy_id = copied.get_json()['id']
    assert copy_id != original.id

    client.put(f'/api/content/{original.id}', json={'title': 'Matrix Reloaded'}, headers=auth_header(client, 'admin', 'admin-password'))
    copy = db.session.get(Content, copy_id)
    assert copy.title == 'Matrix'


def test_suggestions_ignore_inactive_content_and_accounts(client, app):
    from src.models.user import STATUS_PENDING
    admin = create_admin()
    pending = create_user('pendente', 'senha1234', status=STATUS_PENDING)
    maria = create_user('maria', 'senha1234')
    add_content(admin, title='Inativo Admin', active=False)
    add_content(pending, title='Pendente Filme')
    add_content(admin, title='Ativo Admin')
    headers = auth_header(client, 'maria', 'senha1234')

    suggestions = client.get('/api/content/suggestions?q=ati', headers=headers)
    titles = [item['title'] for item in suggestions.get_json()]
    assert 'Ativo Admin' in titles
    assert 'Inativo Admin' not in titles
    assert 'Pendente Filme' not in titles


def test_inactive_platform_is_hidden_from_public_lists(client, app):
    admin = create_admin()
    visible = add_platform('Netflix')
    hidden = add_platform('Oculta')
    hidden.active = False
    db.session.commit()
    add_content(admin, title='Filme Admin', streamings=[visible, hidden])

    public = client.get('/api/streamings')
    public_names = {item['name'] for item in public.get_json()}
    assert 'Netflix' in public_names
    assert 'Oculta' not in public_names

    including_inactive = client.get('/api/streamings?active_only=false')
    all_names = {item['name'] for item in including_inactive.get_json()}
    assert 'Oculta' in all_names

    watchlist = client.get('/api/watchlists')
    streamings = watchlist.get_json()['contents'][0]['streamings']
    assert [item['name'] for item in streamings] == ['Netflix']


def test_editing_content_keeps_links_to_inactive_platforms(client, app):
    admin = create_admin()
    visible = add_platform('Netflix')
    hidden = add_platform('Oculta')
    content = add_content(admin, title='Filme Admin', streamings=[visible, hidden])
    hidden.active = False
    db.session.commit()
    headers = auth_header(client, 'admin', 'admin-password')

    response = client.put(
        f'/api/content/{content.id}',
        json={'year': 2000, 'streaming_ids': [visible.id]},
        headers=headers,
    )
    assert response.status_code == 200
    assert [item['name'] for item in response.get_json()['streamings']] == ['Netflix']

    hidden.active = True
    db.session.commit()
    names = {item['name'] for item in client.get(f'/api/content/{content.id}').get_json()['streamings']}
    assert names == {'Netflix', 'Oculta'}


def test_platform_name_is_trimmed_and_validated(client, app):
    create_admin()
    headers = auth_header(client, 'admin', 'admin-password')

    for name in ('', '   ', None, 'x' * 101):
        response = client.post('/api/streamings', json={'name': name}, headers=headers)
        assert response.status_code == 400

    created = client.post('/api/streamings', json={'name': '  Foo  '}, headers=headers)
    assert created.status_code == 201
    assert created.get_json()['name'] == 'Foo'
    platform_id = created.get_json()['id']

    duplicate = client.post('/api/streamings', json={'name': ' Foo'}, headers=headers)
    assert duplicate.status_code == 400

    blank = client.put(f'/api/streamings/{platform_id}', json={'name': '  '}, headers=headers)
    assert blank.status_code == 400

    renamed = client.put(f'/api/streamings/{platform_id}', json={'name': ' Bar '}, headers=headers)
    assert renamed.status_code == 200
    assert renamed.get_json()['name'] == 'Bar'


def test_only_admin_manages_platforms(client, app):
    create_admin()
    create_user('maria', 'senha1234')
    maria_headers = auth_header(client, 'maria', 'senha1234')
    forbidden = client.post('/api/streamings', json={'name': 'Foo'}, headers=maria_headers)
    assert forbidden.status_code == 403

    admin_headers = auth_header(client, 'admin', 'admin-password')
    created = client.post('/api/streamings', json={'name': 'Foo', 'color': '#000000'}, headers=admin_headers)
    assert created.status_code == 201


def test_missing_resources_return_json_404(client, app):
    create_admin()
    headers = auth_header(client, 'admin', 'admin-password')

    for response in (
        client.get('/api/content/9999'),
        client.put('/api/streamings/9999', json={'name': 'X'}, headers=headers),
        client.delete('/api/streamings/9999', headers=headers),
        client.get('/api/rota-inexistente'),
    ):
        assert response.status_code == 404
        assert response.get_json() == {'error': 'Recurso não encontrado.'}
