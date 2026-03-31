# models/empresa.py
from datetime import datetime
from core.database import Database
import json

class Empresa:
    CORES_PADRAO = {
        'primaria': '#2563eb',
        'secundaria': '#10b981',
        'destaque': '#f59e0b',
        'texto': '#1f2937',
        'fundo': '#f3f4f6'
    }
    
    STATUS_VALIDOS = ['trial', 'ativo', 'inativo', 'suspenso']
    
    def __init__(self, id=None, nome=None, cnpj=None, email=None, telefone=None,
                 celular=None, endereco=None, logo_path=None, status='trial',
                 data_expiracao=None, paleta_cores=None, data_criacao=None, data_atualizacao=None):
        self.id = id
        self.nome = nome
        self.cnpj = cnpj
        self.email = email
        self.telefone = telefone
        self.celular = celular
        self.endereco = endereco
        self.logo_path = logo_path
        self.status = status if status in self.STATUS_VALIDOS else 'trial'
        self.data_expiracao = data_expiracao
        self.paleta_cores = self._processar_cores(paleta_cores)
        self.data_criacao = data_criacao or datetime.now()
        self.data_atualizacao = data_atualizacao or datetime.now()
    
    def _processar_cores(self, paleta_cores):
        if isinstance(paleta_cores, str):
            try:
                return json.loads(paleta_cores)
            except json.JSONDecodeError:
                return self.CORES_PADRAO.copy()
        return paleta_cores or self.CORES_PADRAO.copy()
    
    def save(self):
        db = Database()
        try:
            if self.id:
                return self._atualizar(db)
            return self._criar(db)
        except Exception as e:
            print(f"Erro ao salvar empresa: {e}")
            return None
    
    def _atualizar(self, db):
        query = """
            UPDATE empresas SET
                nome = %s, email = %s, telefone = %s, celular = %s,
                endereco = %s, logo_path = %s, status = %s,
                data_expiracao = %s, paleta_cores = %s,
                data_atualizacao = NOW()
            WHERE id = %s
        """
        params = (
            self.nome, self.email, self.telefone, self.celular,
            self.endereco, self.logo_path, self.status, self.data_expiracao,
            json.dumps(self.paleta_cores), self.id
        )
        db.execute(query, params)
        return self.id
    
    def _criar(self, db):
        query = """
            INSERT INTO empresas (
                nome, cnpj, email, telefone, celular, endereco,
                logo_path, status, data_expiracao, paleta_cores
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            self.nome, self.cnpj, self.email, self.telefone, self.celular,
            self.endereco, self.logo_path, self.status, self.data_expiracao,
            json.dumps(self.paleta_cores)
        )
        self.id = db.execute_return_id(query, params)
        return self.id
    
    @staticmethod
    def get_by_id(empresa_id):
        db = Database()
        result = db.fetch_one("SELECT * FROM empresas WHERE id = %s", (empresa_id,))
        return Empresa(**result) if result else None
    
    @staticmethod
    def get_by_cnpj(cnpj):
        db = Database()
        result = db.fetch_one("SELECT * FROM empresas WHERE cnpj = %s", (cnpj,))
        return Empresa(**result) if result else None
    
    @staticmethod
    def listar_todas(apenas_ativas=False):
        db = Database()
        if apenas_ativas:
            query = "SELECT * FROM empresas WHERE status IN ('ativo', 'trial') ORDER BY nome"
        else:
            query = "SELECT * FROM empresas ORDER BY nome"
        results = db.fetch_all(query)
        return [Empresa(**row) for row in results] if results else []
    
    @staticmethod
    def listar_ativas():
        return Empresa.listar_todas(apenas_ativas=True)
    
    def get_usuarios(self):
        from models.usuario import Usuario
        return Usuario.listar_por_empresa(self.id)
    
    def get_contratos(self):
        from models.contrato import Contrato
        return Contrato.listar_por_empresa(self.id)
    
    def is_active(self):
        if self.status == 'ativo':
            return True
        if self.status == 'trial' and self.data_expiracao:
            return self.data_expiracao > datetime.now()
        return False
    
    def __repr__(self):
        return f"<Empresa {self.id}: {self.nome}>"