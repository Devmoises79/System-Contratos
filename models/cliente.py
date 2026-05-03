from core.database import Database
from datetime import datetime

class Cliente:
    """Modelo de Cliente/Contratante"""
    
    def __init__(self, id=None, empresa_id=None, nome=None, documento=None,
                 email=None, telefone=None, endereco=None, contato_nome=None,
                 contato_telefone=None, contato_email=None, ativo=True,
                 observacoes=None, data_criacao=None, data_atualizacao=None):
        
        self.id = id
        self.empresa_id = empresa_id
        self.nome = nome
        self.documento = documento
        self.email = email
        self.telefone = telefone
        self.endereco = endereco
        self.contato_nome = contato_nome
        self.contato_telefone = contato_telefone
        self.contato_email = contato_email
        self.ativo = ativo
        self.observacoes = observacoes
        self.data_criacao = data_criacao
        self.data_atualizacao = data_atualizacao or datetime.now()
    
    def save(self):
        """Salva cliente (insert ou update)"""
        if self.id:
            query = """
                UPDATE clientes SET
                    nome = %s, documento = %s, email = %s, telefone = %s,
                    endereco = %s, contato_nome = %s, contato_telefone = %s,
                    contato_email = %s, ativo = %s, observacoes = %s,
                    data_atualizacao = NOW()
                WHERE id = %s AND empresa_id = %s
            """
            params = (self.nome, self.documento, self.email, self.telefone,
                     self.endereco, self.contato_nome, self.contato_telefone,
                     self.contato_email, self.ativo, self.observacoes,
                     self.id, self.empresa_id)
            Database.execute(query, params)
            return self.id
        else:
            query = """
                INSERT INTO clientes (
                    empresa_id, nome, documento, email, telefone, endereco,
                    contato_nome, contato_telefone, contato_email, ativo, observacoes,
                    data_criacao, data_atualizacao
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            params = (self.empresa_id, self.nome, self.documento, self.email,
                     self.telefone, self.endereco, self.contato_nome,
                     self.contato_telefone, self.contato_email, self.ativo,
                     self.observacoes)
            self.id = Database.execute_return_id(query, params)
            return self.id
    
    @staticmethod
    def get_by_id(cliente_id, empresa_id):
        """Busca cliente por ID"""
        result = Database.fetch_one(
            "SELECT * FROM clientes WHERE id = %s AND empresa_id = %s",
            (cliente_id, empresa_id)
        )
        return Cliente(**result) if result else None
    
    @staticmethod
    def listar_por_empresa(empresa_id, ativo=None):
        """Lista clientes da empresa"""
        if ativo is not None:
            results = Database.fetch_all(
                "SELECT * FROM clientes WHERE empresa_id = %s AND ativo = %s ORDER BY nome ASC",
                (empresa_id, ativo)
            )
        else:
            results = Database.fetch_all(
                "SELECT * FROM clientes WHERE empresa_id = %s ORDER BY nome ASC",
                (empresa_id,)
            )
        return [Cliente(**row) for row in results] if results else []
    
    @staticmethod
    def buscar(empresa_id, termo):
        """Busca clientes por nome, documento ou email"""
        results = Database.fetch_all("""
            SELECT * FROM clientes 
            WHERE empresa_id = %s AND ativo = 1
            AND (nome LIKE %s OR documento LIKE %s OR email LIKE %s)
            ORDER BY nome ASC
            LIMIT 10
        """, (empresa_id, f"%{termo}%", f"%{termo}%", f"%{termo}%"))
        return [Cliente(**row) for row in results] if results else []
    
    @staticmethod
    def get_contratos(cliente_id, empresa_id):
        """Busca contratos associados ao cliente"""
        results = Database.fetch_all("""
            SELECT * FROM contratos 
            WHERE empresa_id = %s AND contratante_nome = (
                SELECT nome FROM clientes WHERE id = %s AND empresa_id = %s
            )
            ORDER BY data_criacao DESC
        """, (empresa_id, cliente_id, empresa_id))
        return results if results else []
    
    def get_contratos_count(self):
        """Quantidade de contratos associados"""
        result = Database.fetch_one("""
            SELECT COUNT(*) as total FROM contratos 
            WHERE empresa_id = %s AND contratante_nome = %s
        """, (self.empresa_id, self.nome))
        return result['total'] if result else 0
    
    def get_valor_total_contratos(self):
        """Valor total dos contratos associados"""
        result = Database.fetch_one("""
            SELECT SUM(valor) as total FROM contratos 
            WHERE empresa_id = %s AND contratante_nome = %s
        """, (self.empresa_id, self.nome))
        return float(result['total']) if result and result['total'] else 0
    
    def delete(self):
        """Desativa cliente (soft delete)"""
        Database.execute(
            "UPDATE clientes SET ativo = 0 WHERE id = %s AND empresa_id = %s",
            (self.id, self.empresa_id)
        )
        self.ativo = False
        return True
    
    def ativar(self):
        """Ativa cliente"""
        Database.execute(
            "UPDATE clientes SET ativo = 1 WHERE id = %s AND empresa_id = %s",
            (self.id, self.empresa_id)
        )
        self.ativo = True
        return True