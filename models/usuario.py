# models/usuario.py
from datetime import datetime
from core.database import Database
from core.hash_utils import hash_manager
from core.logging_config import logger


class Usuario:
    """Modelo de Usuário do sistema"""
    
    PERFIS = {
        'admin_sistema': 'Administrador do Sistema',
        'admin_empresa': 'Administrador da Empresa',
        'gestor': 'Gestor',
        'analista': 'Analista',
        'assistente': 'Assistente'
    }
    
    def __init__(self, id=None, empresa_id=None, nome=None, email=None,
                 senha_hash=None, perfil='assistente', ativo=1,
                 avatar=None, avatar_path=None, foto=None,
                 ultimo_login=None, ultimo_ip=None,
                 data_criacao=None, data_atualizacao=None,
                 **kwargs):
        self.id = id
        self.empresa_id = empresa_id
        self.nome = nome
        self.email = email
        self.senha_hash = senha_hash
        self.perfil = perfil
        self.ativo = ativo
        
        # Tratar campos de avatar/foto (compatibilidade com banco)
        if avatar:
            self.avatar = avatar
        elif avatar_path:
            self.avatar = avatar_path
        elif foto:
            self.avatar = foto
        else:
            self.avatar = None
        
        self.avatar_path = self.avatar
        self.ultimo_login = ultimo_login
        self.ultimo_ip = ultimo_ip
        self.data_criacao = data_criacao or datetime.now()
        self.data_atualizacao = data_atualizacao or datetime.now()
    
    def save(self):
        """Salva ou atualiza o usuário no banco"""
        if self.id:
            query = """
                UPDATE usuarios SET
                    nome = %s, email = %s, perfil = %s, ativo = %s,
                    avatar = %s, ultimo_login = %s, ultimo_ip = %s,
                    data_atualizacao = NOW()
                WHERE id = %s
            """
            params = (self.nome, self.email, self.perfil, self.ativo,
                     self.avatar, self.ultimo_login, self.ultimo_ip, self.id)
            Database.execute(query, params)
            return self.id
        else:
            query = """
                INSERT INTO usuarios (
                    empresa_id, nome, email, senha_hash, perfil, ativo, avatar
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            params = (self.empresa_id, self.nome, self.email, 
                     self.senha_hash, self.perfil, self.ativo, self.avatar)
            self.id = Database.execute_return_id(query, params)
            return self.id
    
    def set_senha(self, senha):
        """Define uma nova senha para o usuário (gera hash bcrypt)"""
        self.senha_hash = hash_manager.hash_senha(senha)
        if self.id:
            Database.execute(
                "UPDATE usuarios SET senha_hash = %s WHERE id = %s",
                (self.senha_hash, self.id)
            )
        return True
    
    def verificar_senha(self, senha):
        """Verifica se a senha está correta"""
        if not self.senha_hash:
            return False
        return hash_manager.verificar_senha(senha, self.senha_hash)
    
    def get_perfil_display(self):
        """Retorna o nome amigável do perfil"""
        return self.PERFIS.get(self.perfil, self.perfil)
    
    def get_avatar_url(self):
        """Retorna a URL do avatar"""
        if self.avatar:
            return f"/static/uploads/avatars/{self.avatar}"
        # Avatar padrão baseado no perfil
        return f"/static/img/avatars/default.png"
    
    def registrar_login(self, ip=None):
        """Registra o último login do usuário"""
        self.ultimo_login = datetime.now()
        self.ultimo_ip = ip
        Database.execute(
            "UPDATE usuarios SET ultimo_login = NOW(), ultimo_ip = %s WHERE id = %s",
            (ip, self.id)
        )
    
    @staticmethod
    def get_by_id(usuario_id):
        """Busca usuário por ID"""
        result = Database.fetch_one("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
        if result:
            return Usuario(**result)
        return None
    
    @staticmethod
    def get_by_email(email):
        """Busca usuário por email"""
        result = Database.fetch_one("SELECT * FROM usuarios WHERE email = %s", (email,))
        if result:
            return Usuario(**result)
        return None
    
    @staticmethod
    def listar_todos(apenas_ativos=False):
        """Lista todos os usuários"""
        if apenas_ativos:
            results = Database.fetch_all("SELECT * FROM usuarios WHERE ativo = 1 ORDER BY nome")
        else:
            results = Database.fetch_all("SELECT * FROM usuarios ORDER BY nome")
        
        usuarios = []
        for row in results:
            try:
                usuarios.append(Usuario(**row))
            except Exception as e:
                logger.error(f"Erro ao criar usuário: {e}")
                continue
        return usuarios
    
    @staticmethod
    def listar_por_empresa(empresa_id, apenas_ativos=False):
        """Lista usuários de uma empresa"""
        try:
            if apenas_ativos:
                results = Database.fetch_all(
                    "SELECT * FROM usuarios WHERE empresa_id = %s AND ativo = 1 ORDER BY nome",
                    (empresa_id,)
                )
            else:
                results = Database.fetch_all(
                    "SELECT * FROM usuarios WHERE empresa_id = %s ORDER BY nome",
                    (empresa_id,)
                )
            
            usuarios = []
            for row in results:
                try:
                    usuarios.append(Usuario(**row))
                except Exception as e:
                    logger.error(f"Erro ao criar usuário: {e}")
                    continue
            return usuarios
        except Exception as e:
            logger.error(f"Erro em listar_por_empresa: {e}")
            return []
    
    @staticmethod
    def listar_por_perfil(perfil, empresa_id=None):
        """Lista usuários por perfil"""
        if empresa_id:
            results = Database.fetch_all(
                "SELECT * FROM usuarios WHERE perfil = %s AND empresa_id = %s AND ativo = 1 ORDER BY nome",
                (perfil, empresa_id)
            )
        else:
            results = Database.fetch_all(
                "SELECT * FROM usuarios WHERE perfil = %s AND ativo = 1 ORDER BY nome",
                (perfil,)
            )
        
        usuarios = []
        for row in results:
            try:
                usuarios.append(Usuario(**row))
            except Exception as e:
                logger.error(f"Erro ao criar usuário: {e}")
                continue
        return usuarios
    
    @staticmethod
    def autenticar(email, senha):
        """Autentica um usuário"""
        usuario = Usuario.get_by_email(email)
        if usuario and usuario.ativo and usuario.verificar_senha(senha):
            return usuario
        return None
    
    def to_dict(self):
        """Converte usuário para dicionário"""
        return {
            'id': self.id,
            'empresa_id': self.empresa_id,
            'nome': self.nome,
            'email': self.email,
            'perfil': self.perfil,
            'perfil_display': self.get_perfil_display(),
            'ativo': self.ativo,
            'avatar': self.avatar,
            'avatar_url': self.get_avatar_url(),
            'ultimo_login': self.ultimo_login.strftime('%d/%m/%Y %H:%M') if self.ultimo_login else None,
            'ultimo_ip': self.ultimo_ip,
            'data_criacao': self.data_criacao.strftime('%d/%m/%Y %H:%M') if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.strftime('%d/%m/%Y %H:%M') if self.data_atualizacao else None
        }
    
    def __repr__(self):
        return f"<Usuario {self.id}: {self.email} ({self.perfil})>"