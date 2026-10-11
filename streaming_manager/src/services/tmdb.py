"""Cliente mínimo da API do TMDB (The Movie Database) para pré-preencher conteúdos."""
import json
from functools import lru_cache
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.utils.validators import MAX_TITLE_LENGTH

API_BASE = 'https://api.themoviedb.org/3'
POSTER_BASE = 'https://image.tmdb.org/t/p/w500'
THUMBNAIL_BASE = 'https://image.tmdb.org/t/p/w92'
LANGUAGE = 'pt-BR'
TIMEOUT_SECONDS = 5
MAX_RESULTS = 8
MAX_GENRES = 3
ANIMATION_GENRE_ID = 16
MEDIA_TYPES = {'movie': 'movie', 'tv': 'series'}
# Gêneros de séries que o TMDB não traduz para pt-BR.
GENRE_TRANSLATIONS = {
    'Action & Adventure': 'Ação e Aventura',
    'Kids': 'Infantil',
    'News': 'Notícias',
    'Reality': 'Reality show',
    'Sci-Fi & Fantasy': 'Ficção científica e Fantasia',
    'Soap': 'Novela',
    'Talk': 'Talk show',
    'War & Politics': 'Guerra e Política',
}


class TmdbError(Exception):
    """Falha ao consultar o TMDB (rede, chave inválida, resposta inesperada)."""


def _get(path, api_key, **params):
    headers = {'Accept': 'application/json'}
    # O token de leitura (v4) é um JWT; a chave v3 é um hex de 32 caracteres. Aceitamos ambos.
    if '.' in api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    else:
        params['api_key'] = api_key
    request = Request(f'{API_BASE}{path}?{urlencode(params)}', headers=headers)
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.load(response)
    except (URLError, TimeoutError, ValueError) as exc:
        raise TmdbError(str(exc)) from exc


@lru_cache(maxsize=1)
def _genre_names(api_key):
    """Mapa id -> nome dos gêneros de filmes e séries. Muda raramente, então fica em memória."""
    names = {}
    for media in ('movie', 'tv'):
        data = _get(f'/genre/{media}/list', api_key, language=LANGUAGE)
        names.update({
            genre['id']: GENRE_TRANSLATIONS.get(genre['name'], genre['name'])
            for genre in data.get('genres', [])
        })
    return names


def _year(date_text):
    year = (date_text or '')[:4]
    return int(year) if year.isdigit() else None


def _content_type(item, media_type):
    if ANIMATION_GENRE_ID in item.get('genre_ids', []) and item.get('original_language') == 'ja':
        return 'anime'
    return MEDIA_TYPES[media_type]


def _to_suggestion(item, genre_names):
    media_type = item['media_type']
    title_key, date_key = ('title', 'release_date') if media_type == 'movie' else ('name', 'first_air_date')
    poster_path = item.get('poster_path')
    genres = [genre_names[gid] for gid in item.get('genre_ids', []) if gid in genre_names]
    return {
        'id': f"{media_type}-{item['id']}",
        'title': (item.get(title_key) or '').strip()[:MAX_TITLE_LENGTH],
        'year': _year(item.get(date_key)),
        'type': _content_type(item, media_type),
        'genre': ', '.join(genres[:MAX_GENRES]) or None,
        'poster_url': f'{POSTER_BASE}{poster_path}' if poster_path else None,
        'thumbnail_url': f'{THUMBNAIL_BASE}{poster_path}' if poster_path else None,
    }


def search(query, api_key):
    """Busca filmes e séries pelo título e devolve dados no formato do formulário de conteúdo."""
    data = _get('/search/multi', api_key, query=query, language=LANGUAGE, include_adult='false')
    items = [
        item for item in data.get('results', [])
        if item.get('media_type') in MEDIA_TYPES
    ][:MAX_RESULTS]
    if not items:
        return []
    genre_names = _genre_names(api_key)
    return [_to_suggestion(item, genre_names) for item in items]
