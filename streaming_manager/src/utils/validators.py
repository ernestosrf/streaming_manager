import re

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
