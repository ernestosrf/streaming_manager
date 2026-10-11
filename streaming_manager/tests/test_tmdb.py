import io
import json
from urllib.error import HTTPError

import pytest

from src.services import tmdb
from tests.conftest import auth_header, create_admin, create_user

GENRES = {
    '/genre/movie/list': {'genres': [
        {'id': 28, 'name': 'Ação'},
        {'id': 878, 'name': 'Ficção científica'},
        {'id': 16, 'name': 'Animação'},
        {'id': 14, 'name': 'Fantasia'},
    ]},
    '/genre/tv/list': {'genres': [
        {'id': 18, 'name': 'Drama'},
        {'id': 16, 'name': 'Animação'},
        {'id': 10759, 'name': 'Action & Adventure'},
    ]},
}

SEARCH_RESULTS = {'results': [
    {
        'id': 603,
        'media_type': 'movie',
        'title': 'Matrix',
        'release_date': '1999-03-30',
        'genre_ids': [28, 878],
        'original_language': 'en',
        'poster_path': '/matrix.jpg',
    },
    {
        'id': 1,
        'media_type': 'person',
        'name': 'Keanu Reeves',
    },
    {
        'id': 1396,
        'media_type': 'tv',
        'name': 'Breaking Bad',
        'first_air_date': '2008-01-20',
        'genre_ids': [18, 10759],
        'original_language': 'en',
        'poster_path': None,
    },
    {
        'id': 129,
        'media_type': 'movie',
        'title': 'A Viagem de Chihiro',
        'release_date': '2001-07-20',
        'genre_ids': [16, 14],
        'original_language': 'ja',
        'poster_path': '/chihiro.jpg',
    },
    {
        'id': 999,
        'media_type': 'movie',
        'title': 'Sem data',
        'release_date': '',
        'genre_ids': [],
        'original_language': 'en',
    },
]}


@pytest.fixture
def fake_tmdb(app, monkeypatch):
    app.config['TMDB_API_KEY'] = 'test-key'
    calls = []

    def fake_get(path, api_key, **params):
        calls.append((path, api_key, params))
        if path == '/search/multi':
            return SEARCH_RESULTS
        return GENRES[path]

    monkeypatch.setattr(tmdb, '_get', fake_get)
    tmdb._genre_names.cache_clear()
    yield calls
    tmdb._genre_names.cache_clear()


@pytest.fixture
def user_headers(client, app):
    create_admin()
    create_user('maria', 'senha1234')
    return auth_header(client, 'maria', 'senha1234')


def test_lookup_maps_tmdb_results_to_content_fields(client, user_headers, fake_tmdb):
    response = client.get('/api/content/lookup?q=matrix', headers=user_headers)
    assert response.status_code == 200
    data = response.get_json()

    assert [item['title'] for item in data] == ['Matrix', 'Breaking Bad', 'A Viagem de Chihiro', 'Sem data']
    matrix, breaking_bad, chihiro, no_date = data
    assert matrix == {
        'id': 'movie-603',
        'title': 'Matrix',
        'year': 1999,
        'type': 'movie',
        'genre': 'Ação, Ficção científica',
        'poster_url': 'https://image.tmdb.org/t/p/w500/matrix.jpg',
        'thumbnail_url': 'https://image.tmdb.org/t/p/w92/matrix.jpg',
    }
    assert breaking_bad['type'] == 'series'
    assert breaking_bad['year'] == 2008
    assert breaking_bad['genre'] == 'Drama, Ação e Aventura'
    assert breaking_bad['poster_url'] is None
    assert chihiro['type'] == 'anime'
    assert chihiro['genre'] == 'Animação, Fantasia'
    assert no_date['year'] is None
    assert no_date['genre'] is None

    search_call = fake_tmdb[0]
    assert search_call[0] == '/search/multi'
    assert search_call[1] == 'test-key'
    assert search_call[2]['query'] == 'matrix'
    assert search_call[2]['language'] == 'pt-BR'


def test_lookup_result_is_accepted_by_content_create(client, user_headers, fake_tmdb):
    matrix = client.get('/api/content/lookup?q=matrix', headers=user_headers).get_json()[0]
    payload = {field: matrix[field] for field in ('title', 'year', 'type', 'genre', 'poster_url')}

    created = client.post('/api/content', json={**payload, 'streaming_ids': []}, headers=user_headers)
    assert created.status_code == 201


def test_genres_are_fetched_once(client, user_headers, fake_tmdb):
    client.get('/api/content/lookup?q=matrix', headers=user_headers)
    client.get('/api/content/lookup?q=chihiro', headers=user_headers)

    genre_calls = [call for call in fake_tmdb if call[0].startswith('/genre/')]
    assert len(genre_calls) == 2


def test_lookup_requires_login(client, app, fake_tmdb):
    response = client.get('/api/content/lookup?q=matrix')
    assert response.status_code == 401
    assert fake_tmdb == []


def test_lookup_ignores_short_queries(client, user_headers, fake_tmdb):
    response = client.get('/api/content/lookup?q=m', headers=user_headers)
    assert response.status_code == 200
    assert response.get_json() == []
    assert fake_tmdb == []


def test_lookup_without_api_key_is_unavailable(client, app, user_headers):
    app.config['TMDB_API_KEY'] = None
    response = client.get('/api/content/lookup?q=matrix', headers=user_headers)
    assert response.status_code == 503
    assert 'error' in response.get_json()


def test_lookup_reports_tmdb_failure(client, app, user_headers, monkeypatch):
    app.config['TMDB_API_KEY'] = 'test-key'

    def failing_get(path, api_key, **params):
        raise tmdb.TmdbError('HTTP Error 401: Unauthorized')

    monkeypatch.setattr(tmdb, '_get', failing_get)
    response = client.get('/api/content/lookup?q=matrix', headers=user_headers)
    assert response.status_code == 502
    assert 'error' in response.get_json()


@pytest.mark.parametrize('api_key, expect_bearer', [
    ('0123456789abcdef0123456789abcdef', False),
    ('eyJhbGciOiJIUzI1NiJ9.payload.signature', True),
])
def test_get_supports_v3_key_and_v4_token(monkeypatch, api_key, expect_bearer):
    captured = {}

    def fake_urlopen(request, timeout):
        captured['url'] = request.full_url
        captured['auth'] = request.get_header('Authorization')
        return io.BytesIO(json.dumps({'results': []}).encode())

    monkeypatch.setattr(tmdb, 'urlopen', fake_urlopen)
    assert tmdb._get('/search/multi', api_key, query='matrix') == {'results': []}

    if expect_bearer:
        assert captured['auth'] == f'Bearer {api_key}'
        assert 'api_key' not in captured['url']
    else:
        assert captured['auth'] is None
        assert f'api_key={api_key}' in captured['url']


def test_get_wraps_http_errors(monkeypatch):
    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, 401, 'Unauthorized', {}, None)

    monkeypatch.setattr(tmdb, 'urlopen', fake_urlopen)
    with pytest.raises(tmdb.TmdbError):
        tmdb._get('/search/multi', 'bad-key', query='matrix')
