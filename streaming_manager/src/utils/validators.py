import re
from urllib.parse import urlparse

USERNAME_PATTERN = re.compile(r'^[a-z0-9][a-z0-9-]{1,28}[a-z0-9]$')
RESERVED_USERNAMES = {
    'admin',
    'login',
    'register',
    'api',
    'account',
    'static',
    'health',
    'watchlist',
    'watchlists',
    'me',
}

MIN_PASSWORD_LENGTH = 8
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 30


def validate_username(username, *, allow_reserved=False):
    if not username or not isinstance(username, str):
        return 'Username é obrigatório.'

    if len(username) < MIN_USERNAME_LENGTH or len(username) > MAX_USERNAME_LENGTH:
        return 'Username deve ter entre 3 e 30 caracteres.'

    if not USERNAME_PATTERN.match(username):
        return 'Username deve conter apenas letras minúsculas, números e hífen.'

    if not allow_reserved and username in RESERVED_USERNAMES:
        return 'Este username não está disponível.'

    return None


def validate_password(password):
    if not password or not isinstance(password, str):
        return 'Senha é obrigatória.'

    if len(password) < MIN_PASSWORD_LENGTH:
        return f'A senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres.'

    return None


VALID_CONTENT_TYPES = ('movie', 'series', 'anime')
MAX_TITLE_LENGTH = 200
MAX_GENRE_LENGTH = 100
MAX_POSTER_URL_LENGTH = 500
MIN_YEAR = 1800
MAX_YEAR = 2100


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _clean_optional_text(value, field_label, max_length):
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, f'{field_label} deve ser texto.'
    value = value.strip()
    if len(value) > max_length:
        return None, f'{field_label} deve ter no máximo {max_length} caracteres.'
    return value or None, None


def _clean_year(value):
    if value is None or value == '':
        return None, None
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value.strip())
    if not _is_int(value) or not MIN_YEAR <= value <= MAX_YEAR:
        return None, f'Ano deve ser um número entre {MIN_YEAR} e {MAX_YEAR}.'
    return value, None


def _clean_poster_url(value):
    url, error = _clean_optional_text(value, 'URL do poster', MAX_POSTER_URL_LENGTH)
    if error or url is None:
        return url, error
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return None, 'URL do poster deve começar com http:// ou https://.'
    return url, None


def _clean_streaming_ids(value):
    if not isinstance(value, list) or not all(_is_int(item) for item in value):
        return None, 'streaming_ids deve ser uma lista de IDs numéricos.'
    return list(dict.fromkeys(value)), None


def validate_content_payload(data, *, partial=False):
    """Valida e normaliza o corpo de criação/edição de conteúdo.

    Com ``partial=True`` apenas os campos presentes são validados (PUT).
    Retorna ``(campos_limpos, erro)``.
    """
    if not isinstance(data, dict):
        return None, 'Corpo da requisição inválido.'

    cleaned = {}

    if 'title' in data or not partial:
        title = data.get('title')
        if not isinstance(title, str) or not title.strip():
            return None, 'Título é obrigatório.'
        title = title.strip()
        if len(title) > MAX_TITLE_LENGTH:
            return None, f'Título deve ter no máximo {MAX_TITLE_LENGTH} caracteres.'
        cleaned['title'] = title

    if 'type' in data or not partial:
        if data.get('type') not in VALID_CONTENT_TYPES:
            return None, 'Tipo deve ser movie, series ou anime.'
        cleaned['type'] = data['type']

    field_cleaners = {
        'year': _clean_year,
        'genre': lambda value: _clean_optional_text(value, 'Gênero', MAX_GENRE_LENGTH),
        'poster_url': _clean_poster_url,
        'streaming_ids': _clean_streaming_ids,
    }
    for field, clean in field_cleaners.items():
        if field in data:
            value, error = clean(data[field])
            if error:
                return None, error
            cleaned[field] = value
        elif not partial:
            cleaned[field] = [] if field == 'streaming_ids' else None

    return cleaned, None
