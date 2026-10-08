from flask import current_app, jsonify


def server_error(action):
    """Registra a exceção atual e devolve um erro genérico, sem detalhes internos."""
    current_app.logger.exception('Erro ao %s', action)
    return jsonify({'error': f'Erro interno ao {action}.'}), 500
