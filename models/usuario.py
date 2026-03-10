# models/usuario.py (COMPLETO)
import bcrypt
from datetime import datetime
from core.database import Database
from flask import current_app

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
    
    def save(self, usuario_criador_id=None):
        """
        Salva ou atualiza o usuário no banco
        Args:
            usuario_criador_id: ID do usuário que está criando (opcional)
        """
        db = Database()
        
        # Validação: empresa_id é obrigatório para perfis que não são admin_sistema
        if self.perfil != 'admin_sistema' and not self.empresa_id:
            raise ValueError("Usuários não-admin precisam estar vinculados a uma empresa")
        
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
                    data_atualizacao = NOW()
                WHERE id = %s
            """
            params = (
                self.nome, self.cargo, self.telefone, self.celular,
                self.email_corporativo, self.avatar_path, self.ativo,
                self.primeiro_acesso, self.perfil, self.id
            )
            db.execute(query, params)
            return self.id
        else:
            # Cria novo usuário - Adaptado para a estrutura atual da tabela (SEM username)
            query = """
                INSERT INTO usuarios 
                (empresa_id, nome, email, senha_hash, perfil, cargo, 
                 telefone, celular, email_corporativo, avatar_path, ativo, 
                 primeiro_acesso)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                self.empresa_id, self.nome, self.email, self.senha_hash,
                self.perfil, self.cargo, self.telefone, self.celular,
                self.email_corporativo, self.avatar_path, 1 if self.ativo else 0, 
                1 if self.primeiro_acesso else 0
            )
            
            if current_app:
                current_app.logger.info(f"Tentando criar usuário: {self.email}")
            
            self.id = db.execute_return_id(query, params)
            
            if not self.id:
                raise Exception("Falha ao inserir usuário no banco")
            
            return self.id
    
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
    
    def registrar_login(self, ip):
        """
        Registra o último login do usuário
        """
        db = Database()
        try:
            query = """
                UPDATE usuarios 
                SET ultimo_login = NOW(), 
                    ultimo_ip = %s,
                    primeiro_acesso = FALSE 
                WHERE id = %s
            """
            db.execute(query, (ip, self.id))
            if current_app:
                current_app.logger.info(f"Login registrado para usuário {self.id} - IP: {ip}")
            return True
        except Exception as e:
            print(f"Erro ao registrar login: {e}")
            return False
    
    @staticmethod
    def get_by_email(email):
        """Busca usuário por email - CORRIGIDO: usa a coluna email, não username"""
        db = Database()
        
        # Busca usando a coluna email (que existe na sua tabela)
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
    def listar_por_empresa(empresa_id, perfil=None, apenas_ativos=True):
        """Lista usuários de uma empresa"""
        db = Database()
        query = "SELECT * FROM usuarios WHERE empresa_id = %s"
        params = [empresa_id]
        
        if apenas_ativos:
            query += " AND ativo = 1"
        
        if perfil:
            query += " AND perfil = %s"
            params.append(perfil)
        
        query += " ORDER BY nome"
        
        results = db.fetch_all(query, params)
        return [Usuario(**row) for row in results] if results else []
    
    def get_perfil_display(self):
        """Retorna o nome do perfil formatado"""
        perfis = {
            'admin_sistema': 'Administrador do Sistema',
            'admin_empresa': 'Administrador da Empresa',
            'gestor': 'Gestor',
            'analista': 'Analista',
            'assistente': 'Assistente'
        }
        return perfis.get(self.perfil, self.perfil)
    
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
            'ativo': self.ativo,
            'primeiro_acesso': self.primeiro_acesso
        }
    
    def __repr__(self):
        return f"<Usuario {self.id}: {self.nome} ({self.perfil})>"