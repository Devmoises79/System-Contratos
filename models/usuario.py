from datetime import datetime
from core.database import Database
from werkzeug.security import generate_password_hash, check_password_hash
from core.logging_config import logger, LoggerMixin
import secrets
from datetime import timedelta
import re

class Usuario(LoggerMixin):
    """Modelo de usuário com logging e validações robustas"""
    
    PERFIS_VALIDOS = ['admin_sistema', 'admin_empresa', 'gestor', 'analista', 'assistente']
    
    def __init__(self, id=None, empresa_id=None, nome=None, email=None, senha_hash=None,
                 perfil='assistente', cargo=None, telefone=None, celular=None,
                 email_corporativo=None, ativo=True, primeiro_acesso=True,
                 ultimo_login=None, ultimo_ip=None, avatar_path=None,
                 token_recuperacao=None, token_expiracao=None,
                 data_criacao=None, data_atualizacao=None):
        self.id = id
        self.empresa_id = empresa_id
        self.nome = nome
        self.email = email
        self.senha_hash = senha_hash
        self.perfil = perfil if perfil in self.PERFIS_VALIDOS else 'assistente'
        self.cargo = cargo
        self.telefone = telefone
        self.celular = celular
        self.email_corporativo = email_corporativo
        self.ativo = ativo
        self.primeiro_acesso = primeiro_acesso
        self.ultimo_login = ultimo_login
        self.ultimo_ip = ultimo_ip
        self.avatar_path = avatar_path
        self.token_recuperacao = token_recuperacao
        self.token_expiracao = token_expiracao
        self.data_criacao = data_criacao or datetime.now()
        self.data_atualizacao = data_atualizacao or datetime.now()
    
    def definir_senha(self, senha):
        """Gera hash da senha - CORRIGIDO: sempre retorna hash válido"""
        if not senha:
            self.log_error("Tentativa de definir senha vazia")
            return False
        
        try:
            # Gera hash usando método pbkdf2:sha256
            self.senha_hash = generate_password_hash(senha, method='pbkdf2:sha256')
            
            # VERIFICAÇÃO CRÍTICA: garantir que o hash não ficou vazio
            if not self.senha_hash or len(self.senha_hash) < 20:
                self.log_error(f"Hash gerado é inválido: {self.senha_hash}")
                return False
            
            self.log_info(f"Senha definida com sucesso, hash length: {len(self.senha_hash)}")
            return True
            
        except Exception as e:
            self.log_error(f"Erro ao gerar hash da senha: {e}")
            return False
    
    @staticmethod
    def validar_forca_senha(senha):
        """Valida se a senha atende aos requisitos de segurança"""
        if len(senha) < 8:
            return False, "A senha deve ter no mínimo 8 caracteres"
        if not re.search(r'[A-Z]', senha):
            return False, "A senha deve conter pelo menos uma letra maiúscula"
        if not re.search(r'[a-z]', senha):
            return False, "A senha deve conter pelo menos uma letra minúscula"
        if not re.search(r'[0-9]', senha):
            return False, "A senha deve conter pelo menos um número"
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', senha):
            return False, "A senha deve conter pelo menos um caractere especial"
        return True, "Senha válida"
    
    def verificar_senha(self, senha):
        """
        Verifica se a senha está correta.
        CORREÇÃO CRÍTICA: Lida com hashes vazios/inválidos
        """
        # CASO 1: Hash vazio ou muito curto
        if not self.senha_hash or len(self.senha_hash) < 20:
            self.log_error(f"Hash inválido para {self.email} - tamanho: {len(self.senha_hash) if self.senha_hash else 0}")
            
            # Se veio uma senha, tenta corrigir
            if senha:
                self.log_info(f"Tentando corrigir hash para {self.email}")
                self.definir_senha(senha)
                self.save()
                # Verifica novamente com o novo hash
                return check_password_hash(self.senha_hash, senha)
            return False
        
        if not senha:
            return False
        
        try:
            resultado = check_password_hash(self.senha_hash, senha)
            
            if resultado:
                self.log_info(f"Login bem-sucedido para {self.email}")
            else:
                self.log_warning(f"Senha incorreta para {self.email}")
            
            return resultado
            
        except ValueError as e:
            self.log_error(f"Erro ao verificar senha: {e}")
            
            # Tenta recriar o hash com a senha fornecida
            if senha:
                self.definir_senha(senha)
                self.save()
                return check_password_hash(self.senha_hash, senha)
            
            return False
        except Exception as e:
            self.log_error(f"Erro inesperado: {e}")
            return False
    
    def gerar_token_recuperacao(self):
        """Gera um token para recuperação de senha"""
        self.token_recuperacao = secrets.token_urlsafe(32)
        self.token_expiracao = datetime.now() + timedelta(hours=24)
        self.save()
        return self.token_recuperacao
    
    def verificar_token_recuperacao(self, token):
        """Verifica se o token é válido"""
        if not self.token_recuperacao or not self.token_expiracao:
            return False
        if self.token_recuperacao != token:
            return False
        if datetime.now() > self.token_expiracao:
            return False
        return True
    
    def limpar_token_recuperacao(self):
        """Limpa o token após uso"""
        self.token_recuperacao = None
        self.token_expiracao = None
        self.save()
    
    def save(self):
        """Salva ou atualiza o usuário no banco"""
        db = Database()
        
        # Validações básicas
        if not self.nome or not self.email:
            self.log_error("Tentativa de salvar usuário sem nome ou email")
            return None
        
        # CRÍTICO: Validar hash antes de salvar
        if not self.id and (not self.senha_hash or len(self.senha_hash) < 20):
            self.log_error(f"Tentativa de criar usuário sem hash válido para {self.email}")
            return None
        
        try:
            if self.id:
                result = self._atualizar(db)
                return result
            else:
                result = self._criar(db)
                return result
        except Exception as e:
            self.log_error(f"Erro ao salvar usuário: {e}")
            return None
    
    def _atualizar(self, db):
        """Atualiza usuário existente"""
        if self.senha_hash:
            query = """
                UPDATE usuarios SET
                    nome = %s, perfil = %s, cargo = %s, telefone = %s,
                    celular = %s, email_corporativo = %s, ativo = %s,
                    primeiro_acesso = %s, senha_hash = %s, avatar_path = %s,
                    token_recuperacao = %s, token_expiracao = %s,
                    data_atualizacao = NOW()
                WHERE id = %s
            """
            params = (
                self.nome, self.perfil, self.cargo, self.telefone,
                self.celular, self.email_corporativo, self.ativo,
                self.primeiro_acesso, self.senha_hash, self.avatar_path,
                self.token_recuperacao, self.token_expiracao, self.id
            )
        else:
            query = """
                UPDATE usuarios SET
                    nome = %s, perfil = %s, cargo = %s, telefone = %s,
                    celular = %s, email_corporativo = %s, ativo = %s,
                    primeiro_acesso = %s, avatar_path = %s,
                    token_recuperacao = %s, token_expiracao = %s,
                    data_atualizacao = NOW()
                WHERE id = %s
            """
            params = (
                self.nome, self.perfil, self.cargo, self.telefone,
                self.celular, self.email_corporativo, self.ativo,
                self.primeiro_acesso, self.avatar_path,
                self.token_recuperacao, self.token_expiracao, self.id
            )
        
        db.execute(query, params)
        return self.id
    
    def _criar(self, db):
        """Cria novo usuário - CORRIGIDO: garante hash válido"""
        # VERIFICAÇÃO CRÍTICA
        if not self.senha_hash or len(self.senha_hash) < 20:
            self.log_error(f"Hash inválido para novo usuário {self.email}: {self.senha_hash}")
            return None
        
        query = """
            INSERT INTO usuarios (
                empresa_id, nome, email, senha_hash, perfil, cargo,
                telefone, celular, email_corporativo, ativo, primeiro_acesso,
                avatar_path, token_recuperacao, token_expiracao
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            self.empresa_id, self.nome, self.email, self.senha_hash,
            self.perfil, self.cargo, self.telefone, self.celular,
            self.email_corporativo, self.ativo, self.primeiro_acesso,
            self.avatar_path, self.token_recuperacao, self.token_expiracao
        )
        return db.execute_return_id(query, params)
    
    def registrar_login(self, ip):
        """Registra o último login do usuário"""
        db = Database()
        query = """
            UPDATE usuarios 
            SET ultimo_login = NOW(), ultimo_ip = %s, 
                primeiro_acesso = FALSE, data_atualizacao = NOW()
            WHERE id = %s
        """
        db.execute(query, (ip, self.id))
        self.ultimo_login = datetime.now()
        self.ultimo_ip = ip
        self.primeiro_acesso = False
    
    @staticmethod
    def get_by_id(usuario_id):
        db = Database()
        result = db.fetch_one("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
        return Usuario(**result) if result else None
    
    @staticmethod
    def get_by_email(email):
        db = Database()
        result = db.fetch_one("SELECT * FROM usuarios WHERE email = %s", (email,))
        return Usuario(**result) if result else None
    
    @staticmethod
    def get_by_token_recuperacao(token):
        db = Database()
        result = db.fetch_one(
            "SELECT * FROM usuarios WHERE token_recuperacao = %s AND token_expiracao > NOW()",
            (token,)
        )
        return Usuario(**result) if result else None
    
    @staticmethod
    def listar_por_empresa(empresa_id, apenas_ativos=False):
        db = Database()
        if apenas_ativos:
            query = "SELECT * FROM usuarios WHERE empresa_id = %s AND ativo = TRUE ORDER BY nome"
        else:
            query = "SELECT * FROM usuarios WHERE empresa_id = %s ORDER BY nome"
        results = db.fetch_all(query, (empresa_id,))
        return [Usuario(**row) for row in results] if results else []
    
    @staticmethod
    def listar_por_perfil(perfil):
        db = Database()
        query = "SELECT * FROM usuarios WHERE perfil = %s ORDER BY nome"
        results = db.fetch_all(query, (perfil,))
        return [Usuario(**row) for row in results] if results else []
    
    def get_perfil_display(self):
        perfis = {
            'admin_sistema': 'Administrador do Sistema',
            'admin_empresa': 'Administrador da Empresa',
            'gestor': 'Gestor',
            'analista': 'Analista',
            'assistente': 'Assistente'
        }
        return perfis.get(self.perfil, self.perfil)
    
    def get_empresa(self):
        from models.empresa import Empresa
        if self.empresa_id:
            return Empresa.get_by_id(self.empresa_id)
        return None
    
    def tem_permissao(self, permissao):
        permissoes = {
            'admin_sistema': ['*'],
            'admin_empresa': ['gerenciar_empresa', 'gerenciar_usuarios', 'gerenciar_contratos', 'visualizar_estatisticas'],
            'gestor': ['aprovar_contratos', 'visualizar_contratos', 'visualizar_estatisticas', 'gerenciar_contratos'],
            'analista': ['visualizar_contratos', 'visualizar_estatisticas', 'exportar_relatorios'],
            'assistente': ['criar_contratos', 'editar_contratos', 'visualizar_contratos']
        }
        
        if self.perfil == 'admin_sistema':
            return True
        
        return permissao in permissoes.get(self.perfil, [])
    
    def __repr__(self):
        return f"<Usuario {self.id}: {self.nome}>"