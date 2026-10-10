from flask import current_app, jsonify, request


def server_error(action):
    """Registra a exceção atual e devolve um erro genérico, sem detalhes internos."""
    current_app.logger.exception('Erro ao %s', action)
    return jsonify({'error': f'Erro interno ao {action}.'}), 500


def json_object_body():
    """Retorna (dados, erro): o corpo JSON como dict, ou uma resposta 400 se não for um objeto.

    Só um corpo vazio vira ``{}``; ``null`` explícito ou JSON malformado também são rejeitados.
    """
    data = request.get_json(silent=True)
    if data is None and not request.get_data(cache=True).strip():
        return {}, None
    if not isinstance(data, dict):
        return None, (jsonify({'error': 'Corpo da requisição inválido.'}), 400)
    return data, None
