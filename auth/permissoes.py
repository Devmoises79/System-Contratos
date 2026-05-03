# auth/permissoes.py
"""
Módulo de permissões e decoradores de autenticação
"""
from functools import wraps
from flask import session, flash, redirect, url_for, request
from core.logging_config import logger


def login_required(f):
    """Decorator para verificar se o usuário está logado"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))  # CORRIGIDO: 'login' em vez de 'auth.login'
        return f(*args, **kwargs)
    return decorated_function


def admin_sistema_required(f):
    """Decorator para verificar se o usuário é admin do sistema"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        
        perfil = session['usuario'].get('perfil')
        if perfil != 'admin_sistema':
            logger.warning(f"Usuário {session['usuario']['email']} tentou acessar área admin do sistema sem permissão")
            flash('Acesso negado. Área restrita a administradores do sistema.', 'danger')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


def admin_empresa_required(f):
    """Decorator para verificar se o usuário é admin da empresa"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        
        perfil = session['usuario'].get('perfil')
        if perfil not in ['admin_sistema', 'admin_empresa']:
            logger.warning(f"Usuário {session['usuario']['email']} tentou acessar área admin da empresa sem permissão")
            flash('Acesso negado. Área restrita a administradores.', 'danger')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


def gestor_required(f):
    """Decorator para verificar se o usuário é gestor ou superior"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        
        perfil = session['usuario'].get('perfil')
        if perfil not in ['admin_sistema', 'admin_empresa', 'gestor']:
            logger.warning(f"Usuário {session['usuario']['email']} tentou acessar área de gestor sem permissão")
            flash('Acesso negado. Área restrita a gestores.', 'danger')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


def analista_required(f):
    """Decorator para verificar se o usuário é analista ou superior"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        
        perfil = session['usuario'].get('perfil')
        if perfil not in ['admin_sistema', 'admin_empresa', 'gestor', 'analista']:
            logger.warning(f"Usuário {session['usuario']['email']} tentou acessar área de analista sem permissão")
            flash('Acesso negado. Área restrita a analistas.', 'danger')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


def permissao_required(perfis_permitidos):
    """Decorator para verificar permissões baseadas no perfil"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario' not in session:
                flash('Faça login para acessar esta página.', 'warning')
                return redirect(url_for('login'))
            
            perfil_usuario = session['usuario'].get('perfil')
            
            if perfil_usuario not in perfis_permitidos:
                logger.warning(f"Usuário {session['usuario']['email']} tentou acessar {f.__name__} sem permissão")
                flash('Você não tem permissão para acessar esta página.', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def pode_criar_contrato():
    """Verifica se o usuário pode criar contratos"""
    if 'usuario' not in session:
        return False
    
    perfil = session['usuario'].get('perfil')
    return perfil in ['admin_sistema', 'admin_empresa', 'gestor', 'analista', 'assistente']


def pode_editar_contrato(contrato_status, criado_por=None):
    """Verifica se o usuário pode editar um contrato"""
    if 'usuario' not in session:
        return False
    
    perfil = session['usuario'].get('perfil')
    usuario_id = session['usuario'].get('id')
    
    if perfil in ['admin_sistema', 'admin_empresa']:
        return True
    
    if perfil in ['gestor', 'analista']:
        return contrato_status in ['rascunho', 'em_analise']
    
    if perfil == 'assistente':
        return contrato_status == 'rascunho' and criado_por == usuario_id
    
    return False


def pode_aprovar_contrato():
    """Verifica se o usuário pode aprovar contratos"""
    if 'usuario' not in session:
        return False
    
    perfil = session['usuario'].get('perfil')
    return perfil in ['admin_sistema', 'admin_empresa', 'gestor']


def pode_analisar_contrato():
    """Verifica se o usuário pode analisar contratos"""
    if 'usuario' not in session:
        return False
    
    perfil = session['usuario'].get('perfil')
    return perfil in ['admin_sistema', 'admin_empresa', 'gestor', 'analista']


def pode_gerenciar_usuarios():
    """Verifica se o usuário pode gerenciar usuários"""
    if 'usuario' not in session:
        return False
    
    perfil = session['usuario'].get('perfil')
    return perfil in ['admin_sistema', 'admin_empresa']


def pode_visualizar_relatorios():
    """Verifica se o usuário pode visualizar relatórios"""
    if 'usuario' not in session:
        return False
    
    perfil = session['usuario'].get('perfil')
    return perfil in ['admin_sistema', 'admin_empresa', 'gestor', 'analista']


def get_usuario_atual():
    """Retorna o usuário atual da sessão"""
    if 'usuario' in session:
        return session['usuario']
    return None


def get_usuario_id():
    """Retorna o ID do usuário atual"""
    if 'usuario' in session:
        return session['usuario'].get('id')
    return None


def get_empresa_id():
    """Retorna o ID da empresa do usuário atual"""
    if 'usuario' in session:
        return session['usuario'].get('empresa_id')
    return None


def get_perfil_usuario():
    """Retorna o perfil do usuário atual"""
    if 'usuario' in session:
        return session['usuario'].get('perfil')
    return None


def is_admin_sistema():
    """Verifica se o usuário atual é admin do sistema"""
    return get_perfil_usuario() == 'admin_sistema'


def is_admin_empresa():
    """Verifica se o usuário atual é admin da empresa"""
    perfil = get_perfil_usuario()
    return perfil in ['admin_sistema', 'admin_empresa']


def is_gestor():
    """Verifica se o usuário atual é gestor ou superior"""
    perfil = get_perfil_usuario()
    return perfil in ['admin_sistema', 'admin_empresa', 'gestor']


def is_analista():
    """Verifica se o usuário atual é analista ou superior"""
    perfil = get_perfil_usuario()
    return perfil in ['admin_sistema', 'admin_empresa', 'gestor', 'analista']


# ==================== EXPORTAÇÕES ====================

__all__ = [
    'login_required',
    'admin_sistema_required',
    'admin_empresa_required',
    'gestor_required',
    'analista_required',
    'permissao_required',
    'pode_criar_contrato',
    'pode_editar_contrato',
    'pode_aprovar_contrato',
    'pode_analisar_contrato',
    'pode_gerenciar_usuarios',
    'pode_visualizar_relatorios',
    'get_usuario_atual',
    'get_usuario_id',
    'get_empresa_id',
    'get_perfil_usuario',
    'is_admin_sistema',
    'is_admin_empresa',
    'is_gestor',
    'is_analista'
]