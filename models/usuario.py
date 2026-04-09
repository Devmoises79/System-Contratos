"""
Modelo de Usuário do System-Contratos
"""
from werkzeug.security import generate_password_hash, check_password_hash
from core.database import Database
from core.logging_config import logger
from datetime import datetime, timedelta
import secrets


class Usuario:
    """Modelo de usuário do sistema"""
    
    PERFIS = {
        'admin_sistema': 'Administrador do Sistema',
        'admin_empresa': 'Administrador da Empresa',
        'gestor': 'Gestor',
        'analista': 'Analista',
        'assistente': 'Assistente'
    }
    
    def __init__(self, id=None, empresa_id=None, nome=None, email=None, 
                 senha_hash=None, perfil='assistente', cargo=None,
                 telefone=None, celular=None, email_corporativo=None,
                 ativo=True, primeiro_acesso=True, data_cadastro=None,
                 ultimo_login=None, empresa_nome=None, avatar_path=None,
                 token_recuperacao=None, token_expiracao=None,
                 ultimo_ip=None, tentativas_falhas=0, bloqueado_ate=None,
                 data_criacao=None,
                 # Campos de gamificação
                 pontos_totais=0, nivel=1, streak_dias=0, ultimo_acesso=None):
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
        self.data_criacao = data_criacao
        self.primeiro_acesso = primeiro_acesso
        self.data_cadastro = data_cadastro
        self.ultimo_login = ultimo_login
        self.empresa_nome = empresa_nome
        self.avatar_path = avatar_path
        self.token_recuperacao = token_recuperacao
        self.token_expiracao = token_expiracao
        self.ultimo_ip = ultimo_ip
        self.tentativas_falhas = tentativas_falhas or 0
        self.bloqueado_ate = bloqueado_ate
        # Gamificação
        self.pontos_totais = pontos_totais if pontos_totais is not None else 0
        self.nivel = nivel if nivel is not None else 1
        self.streak_dias = streak_dias if streak_dias is not None else 0
        self.ultimo_acesso = ultimo_acesso
    
    def definir_senha(self, senha):
        """Define hash da senha"""
        self.senha_hash = generate_password_hash(senha)
        logger.info(f"Senha definida com sucesso, hash length: {len(self.senha_hash) if self.senha_hash else 0}")
    
    def verificar_senha(self, senha):
        """Verifica se a senha está correta"""
        try:
            if not self.senha_hash:
                logger.error(f"[Usuario] Senha hash vazia para usuário {self.email}")
                return False
            resultado = check_password_hash(self.senha_hash, senha)
            return resultado
        except Exception as e:
            logger.error(f"[Usuario] Erro ao verificar senha: {str(e)}")
            return False
    
    def get_perfil_display(self):
        """Retorna o nome legível do perfil"""
        perfis = {
            'admin_sistema': 'Administrador do Sistema',
            'admin_empresa': 'Administrador da Empresa',
            'gestor': 'Gestor',
            'analista': 'Analista',
            'assistente': 'Assistente'
        }
        return perfis.get(self.perfil, self.perfil)
    
    def save(self):
        """Salva ou atualiza o usuário no banco"""
        db = Database()
        if self.id:
            query = """
                UPDATE usuarios 
                SET empresa_id = %s, nome = %s, email = %s, senha_hash = %s,
                    perfil = %s, cargo = %s, telefone = %s, celular = %s,
                    email_corporativo = %s, ativo = %s, primeiro_acesso = %s,
                    avatar_path = %s, token_recuperacao = %s, token_expiracao = %s,
                    ultimo_ip = %s, tentativas_falhas = %s, bloqueado_ate = %s,
                    pontos_totais = %s, nivel = %s, streak_dias = %s, ultimo_acesso = %s
                WHERE id = %s
            """
            db.execute(query, (
                self.empresa_id, self.nome, self.email, self.senha_hash,
                self.perfil, self.cargo, self.telefone, self.celular,
                self.email_corporativo, self.ativo, self.primeiro_acesso,
                self.avatar_path, self.token_recuperacao, self.token_expiracao,
                self.ultimo_ip, self.tentativas_falhas, self.bloqueado_ate,
                self.pontos_totais, self.nivel, self.streak_dias, self.ultimo_acesso,
                self.id
            ))
        else:
            query = """
                INSERT INTO usuarios (empresa_id, nome, email, senha_hash, perfil, cargo,
                                      telefone, celular, email_corporativo, ativo, primeiro_acesso,
                                      avatar_path, token_recuperacao, token_expiracao,
                                      ultimo_ip, tentativas_falhas, bloqueado_ate,
                                      pontos_totais, nivel, streak_dias, ultimo_acesso)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.id = db.execute_return_id(query, (
                self.empresa_id, self.nome, self.email, self.senha_hash,
                self.perfil, self.cargo, self.telefone, self.celular,
                self.email_corporativo, self.ativo, self.primeiro_acesso,
                self.avatar_path, self.token_recuperacao, self.token_expiracao,
                self.ultimo_ip, self.tentativas_falhas, self.bloqueado_ate,
                self.pontos_totais, self.nivel, self.streak_dias, self.ultimo_acesso
            ))
        return self.id
    
    @staticmethod
    def get_by_id(id):
        """Busca usuário por ID"""
        db = Database()
        result = db.fetch_one("SELECT * FROM usuarios WHERE id = %s", (id,))
        if result:
            # Buscar nome da empresa se necessário
            if result.get('empresa_id'):
                empresa = db.fetch_one("SELECT nome FROM empresas WHERE id = %s", (result['empresa_id'],))
                if empresa:
                    result['empresa_nome'] = empresa['nome']
            return Usuario(**result)
        return None
    
    @staticmethod
    def get_by_email(email):
        """Busca usuário por email"""
        db = Database()
        result = db.fetch_one("SELECT * FROM usuarios WHERE email = %s", (email,))
        if result:
            # Buscar nome da empresa se necessário
            if result.get('empresa_id'):
                empresa = db.fetch_one("SELECT nome FROM empresas WHERE id = %s", (result['empresa_id'],))
                if empresa:
                    result['empresa_nome'] = empresa['nome']
            return Usuario(**result)
        return None
    
    @staticmethod
    def listar_por_empresa(empresa_id):
        """Lista todos os usuários de uma empresa"""
        db = Database()
        results = db.fetch_all("SELECT * FROM usuarios WHERE empresa_id = %s ORDER BY nome", (empresa_id,))
        return [Usuario(**row) for row in results] if results else []
    
    @staticmethod
    def listar_por_perfil(empresa_id, perfil):
        """Lista usuários por perfil"""
        db = Database()
        results = db.fetch_all(
            "SELECT * FROM usuarios WHERE empresa_id = %s AND perfil = %s AND ativo = TRUE ORDER BY nome",
            (empresa_id, perfil)
        )
        return [Usuario(**row) for row in results] if results else []
    
    @staticmethod
    def autenticar(email, senha):
        """Autentica um usuário"""
        usuario = Usuario.get_by_email(email)
        if usuario and usuario.verificar_senha(senha) and usuario.ativo:
            # Verificar se está bloqueado
            if usuario.bloqueado_ate and usuario.bloqueado_ate > datetime.now():
                logger.warning(f"Usuário {email} bloqueado até {usuario.bloqueado_ate}")
                return None
            
            # Atualizar último login
            db = Database()
            db.execute("UPDATE usuarios SET ultimo_login = NOW(), tentativas_falhas = 0 WHERE id = %s", (usuario.id,))
            return usuario
        return None
    
    def registrar_tentativa_falha(self):
        """Registra uma tentativa de login falha"""
        self.tentativas_falhas = (self.tentativas_falhas or 0) + 1
        db = Database()
        
        # Bloquear após 5 tentativas
        if self.tentativas_falhas >= 5:
            self.bloqueado_ate = datetime.now() + timedelta(minutes=15)
            db.execute(
                "UPDATE usuarios SET tentativas_falhas = %s, bloqueado_ate = %s WHERE id = %s",
                (self.tentativas_falhas, self.bloqueado_ate, self.id)
            )
            logger.warning(f"Usuário {self.email} bloqueado por 15 minutos")
        else:
            db.execute("UPDATE usuarios SET tentativas_falhas = %s WHERE id = %s", (self.tentativas_falhas, self.id))
    
    def gerar_token_recuperacao(self):
        """Gera token para recuperação de senha"""
        token = secrets.token_urlsafe(32)
        self.token_recuperacao = token
        self.token_expiracao = datetime.now() + timedelta(hours=1)
        db = Database()
        db.execute(
            "UPDATE usuarios SET token_recuperacao = %s, token_expiracao = %s WHERE id = %s",
            (self.token_recuperacao, self.token_expiracao, self.id)
        )
        return token
    
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
    
    def limpar_token_recuperacao(self):
        """Limpa o token de recuperação"""
        self.token_recuperacao = None
        self.token_expiracao = None
        db = Database()
        db.execute("UPDATE usuarios SET token_recuperacao = NULL, token_expiracao = NULL WHERE id = %s", (self.id,))
    
    def atualizar_pontos(self, pontos):
        """Atualiza os pontos totais do usuário"""
        self.pontos_totais = (self.pontos_totais or 0) + pontos
        db = Database()
        db.execute("UPDATE usuarios SET pontos_totais = %s WHERE id = %s", (self.pontos_totais, self.id))
    
    def atualizar_nivel(self, novo_nivel):
        """Atualiza o nível do usuário"""
        self.nivel = novo_nivel
        db = Database()
        db.execute("UPDATE usuarios SET nivel = %s WHERE id = %s", (self.nivel, self.id))
    
    def atualizar_streak(self):
        """Atualiza a sequência de dias trabalhados"""
        hoje = datetime.now().date()
        
        if self.ultimo_acesso:
            if isinstance(self.ultimo_acesso, str):
                ultimo = datetime.strptime(self.ultimo_acesso, '%Y-%m-%d %H:%M:%S').date()
            else:
                ultimo = self.ultimo_acesso.date()
            
            diferenca = (hoje - ultimo).days
            
            if diferenca == 1:
                self.streak_dias = (self.streak_dias or 0) + 1
            elif diferenca > 1:
                self.streak_dias = 1
        else:
            self.streak_dias = 1
        
        self.ultimo_acesso = datetime.now()
        db = Database()
        db.execute(
            "UPDATE usuarios SET streak_dias = %s, ultimo_acesso = %s WHERE id = %s",
            (self.streak_dias, self.ultimo_acesso, self.id)
        )
    
    def __repr__(self):
        return f"<Usuario {self.id}: {self.nome} ({self.perfil})>"