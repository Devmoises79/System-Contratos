# auth/permissoes.py
from functools import wraps
from flask import session, redirect, url_for, flash, jsonify, request

def login_required(f):
    """Decorator: exige login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def perfil_required(*perfis_permitidos):
    """Decorator: exige um dos perfis especificados"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario' not in session:
                flash('Faça login para acessar esta página.', 'warning')
                return redirect(url_for('login'))
            
            usuario = session['usuario']
            if usuario['perfil'] not in perfis_permitidos:
                # Se for requisição AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'erro': 'Acesso negado'}), 403
                
                flash('Você não tem permissão para acessar esta página.', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Decoradores específicos
def admin_sistema_required(f):
    """Apenas admin do sistema"""
    return perfil_required('admin_sistema')(f)

def admin_empresa_required(f):
    """Admin da empresa ou admin do sistema"""
    return perfil_required('admin_empresa', 'admin_sistema')(f)

def gestor_required(f):
    """Gestor, admin empresa ou admin sistema"""
    return perfil_required('gestor', 'admin_empresa', 'admin_sistema')(f)

def assistente_required(f):
    """Assistente, gestor, admin empresa ou admin sistema"""
    return perfil_required('assistente', 'gestor', 'admin_empresa', 'admin_sistema')(f)

def analista_required(f):
    """Analista, gestor, admin empresa ou admin sistema"""
    return perfil_required('analista', 'gestor', 'admin_empresa', 'admin_sistema')(f)

def empresa_ativa_required(f):
    """Verifica se a empresa do usuário está ativa"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        
        # Aqui você pode verificar o status da empresa no banco
        # Por enquanto, apenas passa
        return f(*args, **kwargs)
    return decorated_function