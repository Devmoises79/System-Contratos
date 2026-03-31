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
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'erro': 'Acesso negado'}), 403
                
                flash('Você não tem permissão para acessar esta página.', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==================== DECORADORES POR PERFIL ====================

def admin_sistema_required(f):
    """Apenas admin do sistema"""
    return perfil_required('admin_sistema')(f)

def admin_empresa_required(f):
    """Admin da empresa OU admin do sistema"""
    return perfil_required('admin_empresa', 'admin_sistema')(f)

def gestor_required(f):
    """Gestor, admin empresa ou admin sistema"""
    return perfil_required('gestor', 'admin_empresa', 'admin_sistema')(f)

def analista_required(f):
    """Analista, gestor, admin empresa ou admin sistema"""
    return perfil_required('analista', 'gestor', 'admin_empresa', 'admin_sistema')(f)

def assistente_required(f):
    """Assistente, analista, gestor, admin empresa ou admin sistema"""
    return perfil_required('assistente', 'analista', 'gestor', 'admin_empresa', 'admin_sistema')(f)


# ==================== FUNÇÕES DE VERIFICAÇÃO ====================

def pode_criar_contrato():
    """Verifica se o usuário pode criar contrato"""
    if 'usuario' not in session:
        return False
    perfil = session['usuario']['perfil']
    return perfil in ['assistente', 'analista', 'gestor', 'admin_empresa', 'admin_sistema']

def pode_editar_contrato(contrato):
    """Verifica se pode editar contrato (apenas rascunho não enviado)"""
    if 'usuario' not in session:
        return False
    
    perfil = session['usuario']['perfil']
    
    # Se não for rascunho ou já foi enviado, não pode editar
    if contrato.status != 'rascunho' or contrato.solicitado_aprovacao:
        return False
    
    # Assistentes só editam seus próprios contratos
    if perfil == 'assistente':
        return contrato.criado_por == session['usuario']['id']
    
    # Demais perfis podem editar qualquer contrato da empresa
    return perfil in ['analista', 'gestor', 'admin_empresa', 'admin_sistema']

def pode_enviar_para_analista():
    """Assistente pode enviar para analista"""
    if 'usuario' not in session:
        return False
    perfil = session['usuario']['perfil']
    return perfil in ['assistente']

def pode_enviar_para_gestor():
    """Analista pode enviar para gestor"""
    if 'usuario' not in session:
        return False
    perfil = session['usuario']['perfil']
    return perfil in ['analista', 'assistente']

def pode_aprovar_contrato():
    """Gestor pode aprovar/rejeitar"""
    if 'usuario' not in session:
        return False
    perfil = session['usuario']['perfil']
    return perfil in ['gestor', 'admin_empresa', 'admin_sistema']

def pode_visualizar_todos_contratos():
    """Analista, gestor e admin veem todos os contratos da empresa"""
    if 'usuario' not in session:
        return False
    perfil = session['usuario']['perfil']
    return perfil in ['analista', 'gestor', 'admin_empresa', 'admin_sistema']

def pode_visualizar_estatisticas():
    """Analista e acima veem estatísticas"""
    if 'usuario' not in session:
        return False
    perfil = session['usuario']['perfil']
    return perfil in ['analista', 'gestor', 'admin_empresa', 'admin_sistema']

def pode_gerenciar_usuarios():
    """Apenas admin empresa e admin sistema"""
    if 'usuario' not in session:
        return False
    perfil = session['usuario']['perfil']
    return perfil in ['admin_empresa', 'admin_sistema']