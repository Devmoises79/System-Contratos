# auth/decorators.py
import functools
from flask import session, redirect, url_for, flash, request, jsonify, render_template
from datetime import datetime, timedelta
import secrets
import hmac
from auth.ip_blocker import IPBlocker

def tempo_sessao_required(f):
    """Verifica se a sessão ainda é válida (máx 2 horas)"""
    @functools.wraps(f)
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
    @functools.wraps(f)
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

def log_acesso(f):
    """Registra acesso às rotas (implementação básica)"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Aqui você pode implementar logging
        return f(*args, **kwargs)
    return decorated_function

def empresa_ativa_required(f):
    """Verifica se a empresa do usuário está ativa"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' in session:
            # Aqui você verificaria no banco se a empresa está ativa
            # Por enquanto, apenas passa
            pass
        return f(*args, **kwargs)
    return decorated_function

def csrf_protegido(f):
    """Protege contra CSRF"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            token = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token')
            token_sessao = session.get('_csrf_token')
            
            if not token or not token_sessao or not hmac.compare_digest(token, token_sessao):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'erro': 'CSRF token inválido'}), 403
                
                flash('Erro de validação do formulário.', 'danger')
                return redirect(request.referrer or url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function