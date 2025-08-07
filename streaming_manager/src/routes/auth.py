import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity

auth_bp = Blueprint('auth', __name__)

# Credenciais de admin
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'senha123')

@auth_bp.route('/login', methods=['POST'])
def login():
    """Endpoint para fazer login e obter token JWT"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username e password são obrigatórios'}), 400
        
        # Verificar credenciais
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            # Criar token JWT com expiração de 24 horas
            access_token = create_access_token(
                identity=username,
                expires_delta=timedelta(hours=24)
            )
            
            return jsonify({
                'access_token': access_token,
                'message': 'Login realizado com sucesso',
                'expires_in': '24 horas'
            }), 200
        else:
            return jsonify({'error': 'Credenciais inválidas'}), 401
            
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Verificar se o token é válido"""
    try:
        current_user = get_jwt_identity()
        return jsonify({
            'valid': True,
            'user': current_user,
            'message': 'Token válido'
        }), 200
    except Exception as e:
        return jsonify({'error': f'Token inválido: {str(e)}'}), 401

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout (no JWT, apenas confirma que o token ainda é válido)"""
    try:
        current_user = get_jwt_identity()
        return jsonify({
            'message': f'Logout realizado com sucesso para {current_user}'
        }), 200
    except Exception as e:
        return jsonify({'error': f'Erro no logout: {str(e)}'}), 400

def admin_required(f):
    """Decorator para proteger rotas que precisam de autenticação de admin"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        try:
            current_user = get_jwt_identity()
            if current_user != ADMIN_USERNAME:
                return jsonify({'error': 'Acesso negado. Apenas administradores.'}), 403
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': f'Erro de autenticação: {str(e)}'}), 401
    return decorated_function
