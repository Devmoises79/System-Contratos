# models/empresa.py
import json
from datetime import datetime
from core.database import Database

class Empresa:
    def __init__(self, id=None, nome=None, cnpj=None, email=None, telefone=None,
                 celular=None, endereco=None, logo_path=None, paleta_cores=None,
                 status='trial', data_expiracao=None, data_criacao=None):
        """
        Inicializa uma empresa com todos os campos possíveis do banco
        """
        self.id = id
        self.nome = nome
        self.cnpj = cnpj
        self.email = email
        self.telefone = telefone
        self.celular = celular
        self.endereco = endereco
        self.logo_path = logo_path
        self.paleta_cores = paleta_cores or {
            'primaria': '#4361ee',
            'secundaria': '#06d6a0',
            'destaque': '#ef476f',
            'texto': '#2b2d42',
            'fundo': '#f8f9fa'
        }
        self.status = status
        self.data_expiracao = data_expiracao
        self.data_criacao = data_criacao
    
    @staticmethod
    def get_by_id(empresa_id):
        db = Database()
        query = "SELECT * FROM empresas WHERE id = %s"
        result = db.fetch_one(query, (empresa_id,))
        if result:
            if result['paleta_cores'] and isinstance(result['paleta_cores'], str):
                try:
                    result['paleta_cores'] = json.loads(result['paleta_cores'])
                except:
                    result['paleta_cores'] = {}
            return Empresa(**result)
        return None
    
    @staticmethod
    def get_by_cnpj(cnpj):
        db = Database()
        query = "SELECT * FROM empresas WHERE cnpj = %s"
        result = db.fetch_one(query, (cnpj,))
        if result:
            if result['paleta_cores'] and isinstance(result['paleta_cores'], str):
                try:
                    result['paleta_cores'] = json.loads(result['paleta_cores'])
                except:
                    result['paleta_cores'] = {}
            return Empresa(**result)
        return None
    
    @staticmethod
    def listar_todas(apenas_ativas=False):
        db = Database()
        query = "SELECT * FROM empresas"
        params = []
        
        if apenas_ativas:
            query += " WHERE status = 'ativo' OR status = 'trial'"
        
        query += " ORDER BY nome"
        
        results = db.fetch_all(query, params)
        empresas = []
        for row in results:
            if row['paleta_cores'] and isinstance(row['paleta_cores'], str):
                try:
                    row['paleta_cores'] = json.loads(row['paleta_cores'])
                except:
                    row['paleta_cores'] = {}
            empresas.append(Empresa(**row))
        return empresas
    
    def save(self):
        db = Database()
        if self.id:
            query = """
                UPDATE empresas SET 
                    nome = %s,
                    email = %s,
                    telefone = %s,
                    celular = %s,
                    endereco = %s,
                    logo_path = %s,
                    paleta_cores = %s,
                    status = %s,
                    data_expiracao = %s
                WHERE id = %s
            """
            params = (
                self.nome, self.email, self.telefone, self.celular,
                self.endereco, self.logo_path,
                json.dumps(self.paleta_cores, ensure_ascii=False),
                self.status, self.data_expiracao, self.id
            )
            db.execute(query, params)
            return self.id
        else:
            query = """
                INSERT INTO empresas 
                (nome, cnpj, email, telefone, celular, endereco, 
                 logo_path, paleta_cores, status, data_expiracao)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                self.nome, self.cnpj, self.email, self.telefone, self.celular,
                self.endereco, self.logo_path,
                json.dumps(self.paleta_cores, ensure_ascii=False),
                self.status, self.data_expiracao
            )
            self.id = db.execute_return_id(query, params)
            return self.id
    
    def atualizar_cores(self, cores):
        """Atualiza a paleta de cores"""
        self.paleta_cores.update(cores)
        return self.save()
    
    def get_usuarios(self, apenas_ativos=True):
        """Retorna todos os usuários da empresa"""
        from models.usuario import Usuario
        return Usuario.listar_por_empresa(self.id, apenas_ativos=apenas_ativos)
    
    def get_contratos(self, status=None):
        """Retorna contratos da empresa"""
        from models.contrato import Contrato
        return Contrato.listar_por_empresa(self.id, status)
    
    def to_dict(self):
        """Converte para dicionário (para API/sessão)"""
        return {
            'id': self.id,
            'nome': self.nome,
            'cnpj': self.cnpj,
            'email': self.email,
            'status': self.status,
            'cores': self.paleta_cores,
            'logo': self.logo_path
        }
    
    def __repr__(self):
        return f"<Empresa {self.id}: {self.nome}>"