# auth/login.py
from flask import session, request
from models.usuario import Usuario
from models.empresa import Empresa
from auth.ip_blocker import IPBlocker
from core.database import Database
from datetime import datetime

class LoginManager:
    @staticmethod
    def login(email, senha, lembrar=False):
        """Realiza o login do usuário"""
        ip = request.remote_addr
        
        # Verifica bloqueio de IP
        bloqueado, minutos = IPBlocker.verificar_bloqueio(ip)
        if bloqueado:
            return False, {
                'erro': 'ip_bloqueado',
                'minutos': minutos,
                'mensagem': f'Seu IP foi bloqueado por {minutos} minutos devido a múltiplas tentativas falhas.'
            }
        
        # Busca usuário
        usuario = Usuario.get_by_email(email)
        
        if not usuario or not usuario.verificar_senha(senha):
            # Registra tentativa falha
            IPBlocker.processar_tentativa_falha(ip, email)
            return False, {
                'erro': 'credenciais_invalidas', 
                'mensagem': 'Email ou senha inválidos'
            }
        
        if not usuario.ativo:
            return False, {
                'erro': 'usuario_inativo', 
                'mensagem': 'Usuário inativo. Contate o administrador.'
            }
        
        # Busca empresa (se não for admin_sistema)
        if usuario.perfil != 'admin_sistema':
            empresa = Empresa.get_by_id(usuario.empresa_id)
            if not empresa or empresa.status == 'inativo':
                return False, {
                    'erro': 'empresa_inativa', 
                    'mensagem': 'Empresa inativa. Contate o suporte.'
                }
        
        # Login bem-sucedido
        IPBlocker.processar_tentativa_sucesso(ip)
        
        # Registrar login (agora o método existe!)
        try:
            usuario.registrar_login(ip)
        except Exception as e:
            # Log do erro mas não impede o login
            print(f"Erro ao registrar login: {e}")
        
        # Dados para sessão
        session['usuario'] = {
            'id': usuario.id,
            'nome': usuario.nome,
            'email': usuario.email,
            'perfil': usuario.perfil,
            'empresa_id': usuario.empresa_id,
            'primeiro_acesso': usuario.primeiro_acesso
        }
        
        # Se não for admin_sistema, adiciona dados da empresa
        if usuario.perfil != 'admin_sistema' and usuario.empresa_id:
            empresa = Empresa.get_by_id(usuario.empresa_id)
            if empresa:
                session['empresa'] = {
                    'id': empresa.id,
                    'nome': empresa.nome,
                    'cores': empresa.paleta_cores,
                    'logo': empresa.logo_path
                }
        
        if lembrar:
            session.permanent = True
        
        # Registra log
        LoginManager._registrar_log(usuario.id, usuario.empresa_id, 'login', ip)
        
        # Determina redirect baseado no perfil
        redirect_url = LoginManager._get_redirect(usuario.perfil)
        
        return True, {
            'redirect': redirect_url,
            'primeiro_acesso': usuario.primeiro_acesso,
            'mensagem': 'Login realizado com sucesso!'
        }
    
    @staticmethod
    def logout():
        """Realiza logout"""
        if 'usuario' in session:
            usuario = session['usuario']
            LoginManager._registrar_log(
                usuario['id'], 
                usuario.get('empresa_id'), 
                'logout', 
                request.remote_addr
            )
        session.clear()
        return True
    
    @staticmethod
    def _get_redirect(perfil):
        """Retorna URL baseada no perfil"""
        redirects = {
            'admin_sistema': '/admin/sistema',
            'admin_empresa': '/admin/empresa',
            'gestor': '/dashboard/gestor',
            'assistente': '/dashboard/assistente',
            'analista': '/dashboard/analista'
        }
        return redirects.get(perfil, '/dashboard')
    
    @staticmethod
    def _registrar_log(usuario_id, empresa_id, acao, ip):
        """Registra log de auditoria"""
        try:
            db = Database()
            query = """
                INSERT INTO logs (empresa_id, usuario_id, acao, modulo, ip_address)
                VALUES (%s, %s, %s, 'auth', %s)
            """
            db.execute(query, (empresa_id, usuario_id, acao, ip))
        except Exception as e:
            print(f"Erro ao registrar log: {e}")
    
    @staticmethod
    def usuario_atual():
        """Retorna usuário logado atual"""
        return session.get('usuario')
    
    @staticmethod
    def empresa_atual():
        """Retorna empresa atual"""
        return session.get('empresa')
    
    @staticmethod
    def esta_logado():
        """Verifica se há usuário logado"""
        return 'usuario' in session