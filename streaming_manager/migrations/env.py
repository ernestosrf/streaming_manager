"""Generic single-database configuration for Flask-Migrate."""
import logging
from logging.config import fileConfig

import sqlalchemy as sa
from flask import current_app
from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def get_engine():
    return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace('%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


config.set_main_option('sqlalchemy.url', get_engine_url())
target_db = current_app.extensions['migrate'].db


def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata


def run_migrations_offline():
    url = config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url,
        target_metadata=get_metadata(),
        literal_binds=True,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    conf_args = dict(current_app.extensions['migrate'].configure_args)
    conf_args.setdefault('process_revision_directives', process_revision_directives)
    conf_args['render_as_batch'] = True

    connectable = get_engine()

    with connectable.connect() as connection:
        is_sqlite = connection.dialect.name == 'sqlite'
        if is_sqlite:
            # PRAGMA foreign_keys não pode ser alterado no meio de uma transação.
            # Sem isso, o batch_alter_table tenta DROP TABLE content e quebra
            # porque content_streaming ainda referencia a tabela.
            connection.execute(sa.text('PRAGMA foreign_keys=OFF'))
            connection.commit()

        try:
            context.configure(
                connection=connection,
                target_metadata=get_metadata(),
                **conf_args
            )

            with context.begin_transaction():
                context.run_migrations()
        finally:
            if is_sqlite:
                connection.execute(sa.text('PRAGMA foreign_keys=ON'))
                connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
