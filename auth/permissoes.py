"""
Permissões e decorators de acesso
"""
from functools import wraps
from flask import session, flash, redirect, url_for

def usuario_logado():
    """Verifica se há usuário logado"""
    return 'usuario' in session

def login_required(f):
    """Decorator para exigir login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not usuario_logado():
            flash('Faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def perfil_required(*perfis):
    """Decorator para exigir perfil específico"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not usuario_logado():
                flash('Faça login para acessar esta página.', 'warning')
                return redirect(url_for('login'))
            if session['usuario']['perfil'] not in perfis:
                flash('Você não tem permissão para acessar esta página.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_sistema_required(f):
    """Apenas admin do sistema"""
    return perfil_required('admin_sistema')(f)

def admin_empresa_required(f):
    """Apenas admin da empresa"""
    return perfil_required('admin_empresa', 'admin_sistema')(f)

def gestor_required(f):
    """Apenas gestor"""
    return perfil_required('gestor', 'admin_empresa', 'admin_sistema')(f)

def analista_required(f):
    """Apenas analista"""
    return perfil_required('analista', 'gestor', 'admin_empresa', 'admin_sistema')(f)

def assistente_required(f):
    """Apenas assistente"""
    return perfil_required('assistente', 'analista', 'gestor', 'admin_empresa', 'admin_sistema')(f)

# ============ FUNÇÕES DE PERMISSÃO PARA CONTRATOS ============

def pode_criar_contrato():
    """Verifica se usuário pode criar contrato"""
    if not usuario_logado():
        return False
    perfil = session['usuario']['perfil']
    return perfil in ['assistente', 'analista', 'gestor', 'admin_empresa', 'admin_sistema']

def pode_editar_contrato(contrato):
    """Verifica se o usuário pode editar o contrato"""
    if not usuario_logado():
        return False
    
    usuario = session['usuario']
    perfil = usuario['perfil']
    
    # Admin pode editar qualquer contrato
    if perfil in ['admin_sistema', 'admin_empresa']:
        return True
    
    # Gestor pode editar contratos em rascunho ou em análise
    if perfil == 'gestor':
        return contrato.status in ['rascunho', 'em_analise']
    
    # Analista pode editar contratos em rascunho ou em análise
    if perfil == 'analista':
        return contrato.status in ['rascunho', 'em_analise']
    
    # Assistente só pode editar seus próprios rascunhos
    if perfil == 'assistente':
        return contrato.status == 'rascunho' and contrato.criado_por == usuario['id']
    
    return False

def pode_enviar_para_analista():
    """Verifica se pode enviar para analista"""
    if not usuario_logado():
        return False
    return session['usuario']['perfil'] == 'assistente'

def pode_enviar_para_gestor():
    """Verifica se pode enviar para gestor"""
    if not usuario_logado():
        return False
    return session['usuario']['perfil'] == 'analista'

def pode_aprovar_contrato():
    """Verifica se pode aprovar contrato"""
    if not usuario_logado():
        return False
    return session['usuario']['perfil'] == 'gestor'