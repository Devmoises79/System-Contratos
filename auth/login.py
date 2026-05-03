# auth/login.py
"""
Módulo de autenticação - Rotas de login
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from core.database import Database
from core.hash_utils import hash_manager
from auth.ip_blocker import IPBlocker
import logging

logger = logging.getLogger(__name__)

# Criar o blueprint - ESTA LINHA É ESSENCIAL
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Rota de login"""
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        lembrar = request.form.get('lembrar') == 'on'
        
        # Obter IP do cliente
        client_ip = request.remote_addr
        
        # Verificar se IP está bloqueado
        if IPBlocker.is_blocked(client_ip):
            remaining = IPBlocker.get_block_time_remaining(client_ip)
            flash(f'Muitas tentativas. Aguarde {remaining} minutos para tentar novamente.', 'danger')
            return redirect(url_for('auth.login'))
        
        try:
            # Buscar usuário
            usuario = Database.fetch_one(
                "SELECT * FROM usuarios WHERE email = %s AND ativo = 1",
                (email,)
            )
            
            if not usuario:
                IPBlocker.register_failed_attempt(client_ip)
                flash('Email ou senha inválidos', 'danger')
                return redirect(url_for('auth.login'))
            
            # Verificar senha - tentar diferentes nomes de coluna
            senha_hash = usuario.get('senha_hash') or usuario.get('senha') or ''
            
            if not senha_hash:
                logger.warning(f"Hash vazio para {email}")
                IPBlocker.register_failed_attempt(client_ip)
                flash('Erro na autenticação. Contate o administrador.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Verificar a senha usando o hash_manager
            if not hash_manager.verificar_senha(senha, senha_hash):
                IPBlocker.register_failed_attempt(client_ip)
                flash('Email ou senha inválidos', 'danger')
                return redirect(url_for('auth.login'))
            
            # Login bem-sucedido - limpar tentativas
            IPBlocker.clear_failed_attempts(client_ip)
            
            # Configurar sessão
            session.permanent = lembrar
            session['usuario_id'] = usuario['id']
            session['usuario'] = {
                'id': usuario['id'],
                'nome': usuario['nome'],
                'email': usuario['email'],
                'perfil': usuario['perfil'],
                'empresa_id': usuario.get('empresa_id')
            }
            session['usuario_nome'] = usuario['nome']
            session['usuario_role'] = usuario['perfil']
            session['empresa_id'] = usuario.get('empresa_id')
            
            flash(f'Bem-vindo, {usuario["nome"]}!', 'success')
            
            # Redirecionar baseado no perfil
            if usuario['perfil'] == 'admin_sistema':
                return redirect(url_for('admin_sistema.dashboard'))
            elif usuario['perfil'] == 'admin_empresa':
                return redirect(url_for('admin_empresa.dashboard'))
            elif usuario['perfil'] == 'gestor':
                return redirect(url_for('dashboard_gestor'))
            elif usuario['perfil'] == 'analista':
                return redirect(url_for('dashboard_analista'))
            else:
                return redirect(url_for('dashboard_assistente'))
                
        except Exception as e:
            logger.error(f"Erro no login: {e}")
            flash('Erro interno no servidor. Tente novamente.', 'danger')
            return redirect(url_for('auth.login'))
    
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Rota de logout"""
    session.clear()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('login'))


# ==================== CLASSE LOGIN MANAGER ====================

class LoginManager:
    """Gerenciador de login para compatibilidade com código existente"""
    
    @staticmethod
    def login(email, senha, lembrar=False):
        """Método estático para login"""
        try:
            # Buscar usuário
            usuario = Database.fetch_one(
                "SELECT * FROM usuarios WHERE email = %s AND ativo = 1",
                (email,)
            )
            
            if not usuario:
                return False, {'mensagem': 'Email ou senha inválidos'}
            
            # Verificar senha
            senha_hash = usuario.get('senha_hash') or usuario.get('senha') or ''
            
            if not hash_manager.verificar_senha(senha, senha_hash):
                return False, {'mensagem': 'Email ou senha inválidos'}
            
            # Configurar sessão
            from flask import session as flask_session
            
            flask_session.permanent = lembrar
            flask_session['usuario_id'] = usuario['id']
            flask_session['usuario'] = {
                'id': usuario['id'],
                'nome': usuario['nome'],
                'email': usuario['email'],
                'perfil': usuario['perfil'],
                'empresa_id': usuario.get('empresa_id')
            }
            flask_session['usuario_nome'] = usuario['nome']
            flask_session['usuario_role'] = usuario['perfil']
            flask_session['empresa_id'] = usuario.get('empresa_id')
            
            # Determinar redirect
            if usuario['perfil'] == 'admin_sistema':
                redirect_url = url_for('admin_sistema.dashboard')
            elif usuario['perfil'] == 'admin_empresa':
                redirect_url = url_for('admin_empresa.dashboard')
            elif usuario['perfil'] == 'gestor':
                redirect_url = url_for('dashboard_gestor')
            elif usuario['perfil'] == 'analista':
                redirect_url = url_for('dashboard_analista')
            else:
                redirect_url = url_for('dashboard_assistente')
            
            return True, {'mensagem': 'Login realizado com sucesso!', 'redirect': redirect_url}
            
        except Exception as e:
            logger.error(f"Erro no LoginManager.login: {e}")
            return False, {'mensagem': 'Erro interno no servidor'}
    
    @staticmethod
    def logout():
        """Método estático para logout"""
        from flask import session as flask_session
        flask_session.clear()
        return True


# Instância global para compatibilidade
login_manager = LoginManager()


# ==================== EXPORTAÇÕES PARA O __INIT__.PY ====================
# Estas linhas garantem que o auth/__init__.py possa importar corretamente
__all__ = ['auth_bp', 'login_manager', 'LoginManager']