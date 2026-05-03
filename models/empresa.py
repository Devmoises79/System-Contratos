# models/empresa.py
from datetime import datetime
from core.database import Database
from core.logging_config import logger


class Empresa:
    """Modelo de Empresa"""
    
    STATUS = {
        'trial': 'Avaliação',
        'ativo': 'Ativo',
        'suspenso': 'Suspenso',
        'cancelado': 'Cancelado'
    }
    
    def __init__(self, id=None, nome=None, cnpj=None, email=None,
                 telefone=None, celular=None, endereco=None,
                 cidade=None, estado=None, cep=None, logo=None,
                 logo_path=None, paleta_cores = None, avatar_path = None,
                 status='trial', plano_id=None, data_expiracao=None,
                 data_criacao=None, data_atualizacao=None):
        self.id = id
        self.nome = nome
        self.cnpj = cnpj
        self.email = email
        self.telefone = telefone
        self.celular = celular
        self.endereco = endereco
        self.cidade = cidade
        self.estado = estado
        self.cep = cep
        self.avatar_path = avatar_path
        self.paleta_cores = paleta_cores 
        self.logo = logo or logo_path  # <-- usa logo_path se logo for None
        self.logo_path = logo_path or logo  # <-- ambos para compatibilidade
        self.status = status
        self.plano_id = plano_id
        self.data_expiracao = data_expiracao
        self.data_criacao = data_criacao or datetime.now()
        self.data_atualizacao = data_atualizacao or datetime.now()
    
    def save(self):
        """Salva ou atualiza a empresa no banco"""
        if self.id:
            query = """
                UPDATE empresas SET
                    nome = %s, cnpj = %s, email = %s, telefone = %s,
                    celular = %s, endereco = %s, cidade = %s, estado = %s,
                    cep = %s, logo = %s, status = %s, plano_id = %s,
                    data_expiracao = %s, data_atualizacao = NOW()
                WHERE id = %s
            """
            params = (self.nome, self.cnpj, self.email, self.telefone,
                     self.celular, self.endereco, self.cidade, self.estado,
                     self.cep, self.logo, self.status, self.plano_id,
                     self.data_expiracao, self.id)
            Database.execute(query, params)
            return self.id
        else:
            query = """
                INSERT INTO empresas (
                    nome, cnpj, email, telefone, celular, endereco,
                    cidade, estado, cep, logo, status, plano_id, data_expiracao
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (self.nome, self.cnpj, self.email, self.telefone,
                     self.celular, self.endereco, self.cidade, self.estado,
                     self.cep, self.logo, self.status, self.plano_id,
                     self.data_expiracao)
            self.id = Database.execute_return_id(query, params)
            return self.id
    
    def get_status_display(self):
        """Retorna o nome amigável do status"""
        return self.STATUS.get(self.status, self.status)
    
    def get_usuarios(self):
        """Retorna todos os usuários da empresa"""
        results = Database.fetch_all("SELECT * FROM usuarios WHERE empresa_id = %s", (self.id,))
        from models.usuario import Usuario
        return [Usuario(**row) for row in results] if results else []
    
    def get_contratos(self, status=None):
        """Retorna os contratos da empresa"""
        from models.contrato import Contrato
        return Contrato.listar_por_empresa(self.id, status)
    
    def get_estatisticas(self):
        """Retorna estatísticas da empresa"""
        from models.contrato import Contrato
        return Contrato.estatisticas(self.id)
    
    def is_trial_ativo(self):
        """Verifica se o período de trial ainda está ativo"""
        if self.status != 'trial':
            return False
        if self.data_expiracao:
            if isinstance(self.data_expiracao, str):
                from datetime import datetime as dt
                data_exp = dt.strptime(self.data_expiracao, '%Y-%m-%d').date()
            else:
                data_exp = self.data_expiracao
            return datetime.now().date() <= data_exp
        return True
    
    def get_logo_url(self):
        """Retorna a URL do logo"""
        if self.logo:
            return f"/static/uploads/empresas/{self.logo}"
        return "/static/img/default-company.png"
    
    @staticmethod
    def get_by_id(empresa_id):
        """Busca empresa por ID"""
        result = Database.fetch_one("SELECT * FROM empresas WHERE id = %s", (empresa_id,))
        if result:
            return Empresa(**result)
        return None
    
    @staticmethod
    def get_by_cnpj(cnpj):
        """Busca empresa por CNPJ"""
        result = Database.fetch_one("SELECT * FROM empresas WHERE cnpj = %s", (cnpj,))
        if result:
            return Empresa(**result)
        return None
    
    @staticmethod
    def listar_todos(status=None):
        """Lista todas as empresas"""
        if status:
            results = Database.fetch_all("SELECT * FROM empresas WHERE status = %s ORDER BY nome", (status,))
        else:
            results = Database.fetch_all("SELECT * FROM empresas ORDER BY nome")
        return [Empresa(**row) for row in results] if results else []
    
    @staticmethod
    def listar_ativas():
        """Lista empresas ativas e em trial"""
        results = Database.fetch_all(
            "SELECT * FROM empresas WHERE status IN ('ativo', 'trial') ORDER BY nome"
        )
        return [Empresa(**row) for row in results] if results else []
    
    def to_dict(self):
        """Converte empresa para dicionário"""
        return {
            'id': self.id,
            'nome': self.nome,
            'cnpj': self.cnpj,
            'email': self.email,
            'telefone': self.telefone,
            'celular': self.celular,
            'endereco': self.endereco,
            'cidade': self.cidade,
            'estado': self.estado,
            'cep': self.cep,
            'logo': self.logo,
            'status': self.status,
            'status_display': self.get_status_display(),
            'plano_id': self.plano_id,
            'data_expiracao': self.data_expiracao.strftime('%d/%m/%Y') if self.data_expiracao else None,
            'is_trial_ativo': self.is_trial_ativo()
        }
    
    def __repr__(self):
        return f"<Empresa {self.id}: {self.nome}>"