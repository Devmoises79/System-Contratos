# models/usuario.py - CORRIGIDO
from datetime import datetime
from core.database import Database
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from datetime import timedelta

class Usuario:
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
        self.perfil = perfil
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
        """Gera hash da senha usando método padrão do werkzeug"""
        if not senha:
            return False
        try:
            self.senha_hash = generate_password_hash(senha)
            return True
        except Exception as e:
            print(f"Erro ao gerar hash: {e}")
            return False
    
    def verificar_senha(self, senha):
        """Verifica se a senha está correta"""
        # Verifica se o hash existe
        if not self.senha_hash:
            print(f"DEBUG: Usuário {self.email} não tem hash de senha")
            return False
        
        # Verifica se a senha foi fornecida
        if not senha:
            return False
        
        try:
            # Tenta verificar com o werkzeug
            resultado = check_password_hash(self.senha_hash, senha)
            print(f"DEBUG: Verificação de senha para {self.email}: {resultado}")
            return resultado
        except ValueError as e:
            print(f"DEBUG: Erro de formato de hash - {e}")
            # Se o hash for antigo, tenta recriar
            if "Invalid hash method" in str(e):
                # Recria o hash com o método correto
                self.definir_senha(senha)
                self.save()
                return True
            return False
        except Exception as e:
            print(f"DEBUG: Erro inesperado ao verificar senha: {e}")
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
        
        if self.id:
            # Atualiza usuário existente
            query = """
                UPDATE usuarios SET
                    nome = %s,
                    perfil = %s,
                    cargo = %s,
                    telefone = %s,
                    celular = %s,
                    email_corporativo = %s,
                    ativo = %s,
                    primeiro_acesso = %s,
                    avatar_path = %s,
                    token_recuperacao = %s,
                    token_expiracao = %s,
                    data_atualizacao = NOW()
                WHERE id = %s
            """
            params = (
                self.nome, self.perfil, self.cargo, self.telefone,
                self.celular, self.email_corporativo, self.ativo,
                self.primeiro_acesso, self.avatar_path,
                self.token_recuperacao, self.token_expiracao, self.id
            )
            
            # Se a senha foi alterada, atualiza também
            if self.senha_hash:
                query = """
                    UPDATE usuarios SET
                        nome = %s,
                        perfil = %s,
                        cargo = %s,
                        telefone = %s,
                        celular = %s,
                        email_corporativo = %s,
                        ativo = %s,
                        primeiro_acesso = %s,
                        senha_hash = %s,
                        avatar_path = %s,
                        token_recuperacao = %s,
                        token_expiracao = %s,
                        data_atualizacao = NOW()
                    WHERE id = %s
                """
                params = (
                    self.nome, self.perfil, self.cargo, self.telefone,
                    self.celular, self.email_corporativo, self.ativo,
                    self.primeiro_acesso, self.senha_hash, self.avatar_path,
                    self.token_recuperacao, self.token_expiracao, self.id
                )
            
            db.execute(query, params)
            return self.id
        else:
            # Cria novo usuário
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
            self.id = db.execute_return_id(query, params)
            return self.id
    
    def registrar_login(self, ip):
        """Registra o último login do usuário"""
        db = Database()
        query = """
            UPDATE usuarios 
            SET ultimo_login = NOW(), 
                ultimo_ip = %s, 
                primeiro_acesso = FALSE,
                data_atualizacao = NOW()
            WHERE id = %s
        """
        db.execute(query, (ip, self.id))
        self.ultimo_login = datetime.now()
        self.ultimo_ip = ip
        self.primeiro_acesso = False
    
    @staticmethod
    def get_by_id(usuario_id):
        """Busca usuário por ID"""
        db = Database()
        result = db.fetch_one("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
        if result:
            return Usuario(**result)
        return None
    
    @staticmethod
    def get_by_email(email):
        """Busca usuário por email"""
        db = Database()
        result = db.fetch_one("SELECT * FROM usuarios WHERE email = %s", (email,))
        if result:
            return Usuario(**result)
        return None
    
    @staticmethod
    def get_by_token_recuperacao(token):
        """Busca usuário por token de recuperação"""
        db = Database()
        result = db.fetch_one(
            "SELECT * FROM usuarios WHERE token_recuperacao = %s AND token_expiracao > NOW()",
            (token,)
        )
        if result:
            return Usuario(**result)
        return None
    
    @staticmethod
    def listar_por_empresa(empresa_id, apenas_ativos=False):
        """Lista usuários de uma empresa"""
        db = Database()
        if apenas_ativos:
            query = "SELECT * FROM usuarios WHERE empresa_id = %s AND ativo = TRUE ORDER BY nome"
        else:
            query = "SELECT * FROM usuarios WHERE empresa_id = %s ORDER BY nome"
        results = db.fetch_all(query, (empresa_id,))
        return [Usuario(**row) for row in results] if results else []
    
    @staticmethod
    def listar_por_perfil(perfil):
        """Lista usuários por perfil"""
        db = Database()
        query = "SELECT * FROM usuarios WHERE perfil = %s ORDER BY nome"
        results = db.fetch_all(query, (perfil,))
        return [Usuario(**row) for row in results] if results else []
    
    def get_perfil_display(self):
        """Retorna o nome amigável do perfil"""
        perfis = {
            'admin_sistema': 'Administrador do Sistema',
            'admin_empresa': 'Administrador da Empresa',
            'gestor': 'Gestor',
            'analista': 'Analista',
            'assistente': 'Assistente'
        }
        return perfis.get(self.perfil, self.perfil)
    
    def get_empresa(self):
        """Retorna a empresa do usuário"""
        from models.empresa import Empresa
        if self.empresa_id:
            return Empresa.get_by_id(self.empresa_id)
        return None
    
    def tem_permissao(self, permissao):
        """Verifica se o usuário tem uma permissão específica"""
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