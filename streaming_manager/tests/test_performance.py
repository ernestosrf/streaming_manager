from contextlib import contextmanager

from sqlalchemy import event

from src.models.db import db
from tests.conftest import add_content, add_platform, auth_header, create_admin, create_user


@contextmanager
def count_queries():
    statements = []

    def before_execute(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    engine = db.engine
    event.listen(engine, 'before_cursor_execute', before_execute)
    try:
        yield statements
    finally:
        event.remove(engine, 'before_cursor_execute', before_execute)


def _seed_watchlist(owner, platforms, count):
    for index in range(count):
        add_content(
            owner,
            title=f'Titulo {index:02d}',
            content_type=('movie', 'series', 'anime')[index % 3],
            active=index % 4 != 0,
            streamings=platforms[: (index % len(platforms)) + 1],
        )


def test_stats_counts_by_type_streaming_and_inactive(client, app):
    create_admin()
    maria = create_user('maria', 'senha1234')
    joao = create_user('joao', 'senha1234')
    netflix = add_platform('Netflix')
    prime = add_platform('Prime', color='#00A8E1')
    hidden = add_platform('Antiga', color='#111111')
    hidden.active = False
    db.session.commit()

    _seed_watchlist(maria, [netflix, prime, hidden], 12)
    add_content(joao, title='De outro dono', streamings=[netflix])

    public = client.get('/api/watchlists/maria/stats').get_json()
    # índices 0, 4 e 8 ficam inativos -> 9 ativos (3 de cada tipo)
    assert public['total_content'] == 9
    assert public['total_inactive'] == 0
    assert public['by_type'] == {'movies': 3, 'series': 3, 'animes': 3}
    by_streaming = {item['streaming']['name']: item['count'] for item in public['by_streaming']}
    assert by_streaming == {'Netflix': 9, 'Prime': 6}

    owner_view = client.get('/api/watchlists/maria/stats', headers=auth_header(client, 'maria', 'senha1234')).get_json()
    assert owner_view['total_inactive'] == 3


def test_watchlist_and_stats_do_not_issue_per_item_queries(client, app):
    create_admin()
    maria = create_user('maria', 'senha1234')
    platforms = [add_platform(f'Plataforma {i}', color='#000000') for i in range(5)]
    _seed_watchlist(maria, platforms, 30)
    db.session.expire_all()

    with count_queries() as statements:
        response = client.get('/api/watchlists/maria')
    assert response.status_code == 200
    assert len(response.get_json()['contents']) > 20
    assert len(statements) <= 5, statements

    with count_queries() as statements:
        assert client.get('/api/watchlists/maria/stats').status_code == 200
    assert len(statements) <= 5, statements
