# models/usuario.py
import bcrypt
from datetime import datetime
from core.database import Database

class Usuario:
    def __init__(self, id=None, empresa_id=None, nome=None, email=None, senha_hash=None,
                 perfil=None, cargo=None, telefone=None, celular=None, email_corporativo=None,
                 avatar_path=None, ativo=True, primeiro_acesso=True, ultimo_login=None,
                 ultimo_ip=None, token_recuperacao=None, token_expiracao=None,
                 data_criacao=None, criado_por=None, data_atualizacao=None, atualizado_por=None):
        """
        Inicializa um usuário com todos os campos possíveis do banco
        """
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
        self.avatar_path = avatar_path
        self.ativo = ativo
        self.primeiro_acesso = primeiro_acesso
        self.ultimo_login = ultimo_login
        self.ultimo_ip = ultimo_ip
        self.token_recuperacao = token_recuperacao
        self.token_expiracao = token_expiracao
        self.data_criacao = data_criacao
        self.criado_por = criado_por
        self.data_atualizacao = data_atualizacao
        self.atualizado_por = atualizado_por
    
    @staticmethod
    def get_by_email(email):
        """Busca usuário por email"""
        db = Database()
        query = "SELECT * FROM usuarios WHERE email = %s"
        result = db.fetch_one(query, (email,))
        if result:
            return Usuario(**result)
        return None
    
    @staticmethod
    def get_by_id(usuario_id):
        """Busca usuário por ID"""
        db = Database()
        query = "SELECT * FROM usuarios WHERE id = %s"
        result = db.fetch_one(query, (usuario_id,))
        if result:
            return Usuario(**result)
        return None
    
    @staticmethod
    def get_by_token(token):
        """Busca usuário por token de recuperação"""
        db = Database()
        query = """
            SELECT * FROM usuarios 
            WHERE token_recuperacao = %s 
            AND token_expiracao > NOW()
        """
        result = db.fetch_one(query, (token,))
        if result:
            return Usuario(**result)
        return None
    
    @staticmethod
    def listar_por_empresa(empresa_id, perfil=None, apenas_ativos=True):
        """Lista usuários de uma empresa"""
        db = Database()
        query = "SELECT * FROM usuarios WHERE empresa_id = %s"
        params = [empresa_id]
        
        if apenas_ativos:
            query += " AND ativo = TRUE"
        
        if perfil:
            query += " AND perfil = %s"
            params.append(perfil)
        
        query += " ORDER BY nome"
        
        results = db.fetch_all(query, params)
        return [Usuario(**row) for row in results] if results else []
    
    @staticmethod
    def listar_todos(apenas_ativos=True):
        """Lista todos os usuários do sistema"""
        db = Database()
        query = "SELECT * FROM usuarios"
        params = []
        
        if apenas_ativos:
            query += " WHERE ativo = TRUE"
        
        query += " ORDER BY nome"
        
        results = db.fetch_all(query, params)
        return [Usuario(**row) for row in results] if results else []
    
    def verificar_senha(self, senha):
        """Verifica se a senha está correta"""
        if not self.senha_hash:
            return False
        try:
            return bcrypt.checkpw(
                senha.encode('utf-8'), 
                self.senha_hash.encode('utf-8')
            )
        except Exception as e:
            print(f"Erro ao verificar senha: {e}")
            return False
    
    def definir_senha(self, senha):
        """Define uma nova senha com hash"""
        try:
            salt = bcrypt.gensalt()
            self.senha_hash = bcrypt.hashpw(
                senha.encode('utf-8'), 
                salt
            ).decode('utf-8')
            return True
        except Exception as e:
            print(f"Erro ao definir senha: {e}")
            return False
    
    def save(self):
        """Salva ou atualiza o usuário no banco"""
        db = Database()
        if self.id:
            # Atualiza usuário existente
            query = """
                UPDATE usuarios SET 
                    nome = %s,
                    cargo = %s,
                    telefone = %s,
                    celular = %s,
                    email_corporativo = %s,
                    avatar_path = %s,
                    ativo = %s,
                    primeiro_acesso = %s,
                    perfil = %s,
                    data_atualizacao = NOW(),
                    atualizado_por = %s
                WHERE id = %s
            """
            params = (
                self.nome, self.cargo, self.telefone, self.celular,
                self.email_corporativo, self.avatar_path, self.ativo,
                self.primeiro_acesso, self.perfil, self.atualizado_por, self.id
            )
            db.execute(query, params)
            return self.id
        else:
            # Cria novo usuário
            query = """
                INSERT INTO usuarios 
                (empresa_id, nome, email, senha_hash, perfil, cargo, 
                 telefone, celular, email_corporativo, avatar_path, ativo, 
                 primeiro_acesso, criado_por)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                self.empresa_id, self.nome, self.email, self.senha_hash,
                self.perfil, self.cargo, self.telefone, self.celular,
                self.email_corporativo, self.avatar_path, self.ativo, 
                self.primeiro_acesso, self.criado_por
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
                primeiro_acesso = FALSE 
            WHERE id = %s
        """
        db.execute(query, (ip, self.id))
    
    def gerar_token_recuperacao(self):
        """Gera token para recuperação de senha"""
        import secrets
        from datetime import datetime, timedelta
        
        self.token_recuperacao = secrets.token_urlsafe(32)
        self.token_expiracao = datetime.now() + timedelta(hours=24)
        
        db = Database()
        query = """
            UPDATE usuarios 
            SET token_recuperacao = %s, 
                token_expiracao = %s 
            WHERE id = %s
        """
        db.execute(query, (self.token_recuperacao, self.token_expiracao, self.id))
        
        return self.token_recuperacao
    
    def limpar_token(self):
        """Limpa token de recuperação"""
        self.token_recuperacao = None
        self.token_expiracao = None
        
        db = Database()
        query = """
            UPDATE usuarios 
            SET token_recuperacao = NULL, 
                token_expiracao = NULL 
            WHERE id = %s
        """
        db.execute(query, (self.id,))
    
    def tem_permissao(self, modulo, acao):
        """Verifica se usuário tem permissão (simplificado)"""
        # Admin sistema tem todas as permissões
        if self.perfil == 'admin_sistema':
            return True
        
        # Permissões por perfil (simplificado)
        permissoes = {
            'admin_empresa': {
                'contratos': ['criar', 'ler', 'atualizar', 'apropar'],
                'usuarios': ['criar', 'ler', 'atualizar'],
                'config': ['ler', 'atualizar']
            },
            'gestor': {
                'contratos': ['criar', 'ler', 'atualizar', 'aprovar'],
                'relatorios': ['ler']
            },
            'assistente': {
                'contratos': ['criar', 'ler', 'atualizar']
            },
            'analista': {
                'contratos': ['ler'],
                'relatorios': ['ler']
            }
        }
        
        perfil_perm = permissoes.get(self.perfil, {})
        modulo_perm = perfil_perm.get(modulo, [])
        
        return acao in modulo_perm
    
    def get_perfil_display(self):
        """Retorna o nome do perfil formatado"""
        perfis = {
            'admin_sistema': 'Administrador do Sistema',
            'admin_empresa': 'Administrador da Empresa',
            'gestor': 'Gestor',
            'assistente': 'Assistente',
            'analista': 'Analista'
        }
        return perfis.get(self.perfil, self.perfil)
    
    def get_redirect_url(self):
        """Retorna a URL de redirecionamento baseada no perfil"""
        redirects = {
            'admin_sistema': 'admin_sistema.dashboard',
            'admin_empresa': 'admin_empresa.dashboard',
            'gestor': 'gestor_dashboard',
            'assistente': 'assistente_dashboard',
            'analista': 'analista_dashboard'
        }
        return redirects.get(self.perfil, 'dashboard')
    
    def to_dict(self):
        """Converte para dicionário (para API/sessão)"""
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'perfil': self.perfil,
            'perfil_display': self.get_perfil_display(),
            'cargo': self.cargo,
            'empresa_id': self.empresa_id,
            'email_corporativo': self.email_corporativo,
            'ativo': self.ativo,
            'primeiro_acesso': self.primeiro_acesso,
            'ultimo_login': self.ultimo_login.isoformat() if self.ultimo_login else None
        }
    
    def __repr__(self):
        """Representação do objeto"""
        return f"<Usuario {self.id}: {self.nome} ({self.perfil})>"