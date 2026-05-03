# auth/decorators.py
"""
Permissões e decorators de acesso
"""
from functools import wraps
from flask import session, flash, redirect, url_for, request, jsonify
from datetime import datetime, timedelta
import secrets
import hmac
from auth.ip_blocker import IPBlocker


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


def tempo_sessao_required(f):
    """Verifica se a sessão ainda é válida (máx 2 horas)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' in session:
            if 'login_time' in session:
                try:
                    login_time = datetime.fromisoformat(session['login_time'])
                    if datetime.now() - login_time > timedelta(hours=2):
                        session.clear()
                        flash('Sessão expirada. Faça login novamente.', 'warning')
                        return redirect(url_for('login'))
                except:
                    session.clear()
                    return redirect(url_for('login'))
            
            session['login_time'] = datetime.now().isoformat()
        return f(*args, **kwargs)
    return decorated_function


def ip_bloqueado_verificado(f):
    """Verifica se o IP não está bloqueado"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        bloqueado, minutos = IPBlocker.verificar_bloqueio(ip)
        
        if bloqueado:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'erro': 'ip_bloqueado',
                    'minutos': minutos,
                    'mensagem': f'IP bloqueado por {minutos} minutos'
                }), 403
            
            return render_template('auth/bloqueado.html', 
                                 minutos=minutos,
                                 ip=ip), 403
        return f(*args, **kwargs)
    return decorated_function


def csrf_protegido(f):
    """Protege contra CSRF - CORRIGIDO para AJAX"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            # Para AJAX, pode vir no header
            token = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token')
            token_sessao = session.get('_csrf_token')
            
            if not token or not token_sessao or not hmac.compare_digest(token, token_sessao):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                    return jsonify({'erro': 'CSRF token inválido'}), 403
                
                flash('Erro de validação do formulário.', 'danger')
                return redirect(request.referrer or url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function


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
    
    if perfil in ['admin_sistema', 'admin_empresa']:
        return True
    
    if perfil == 'gestor':
        return contrato.status in ['rascunho', 'em_analise']
    
    if perfil == 'analista':
        return contrato.status in ['rascunho', 'em_analise']
    
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