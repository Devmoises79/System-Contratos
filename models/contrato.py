# models/contrato.py
from datetime import datetime
from core.database import Database

class Contrato:
    def __init__(self, id=None, empresa_id=None, numero_contrato=None, 
                 contratante_nome=None, contratante_cnpj=None, contratante_email=None, 
                 contratante_telefone=None, contratada_nome=None, contratada_cnpj=None, 
                 contratada_email=None, valor=None, prazo_dias=None, data_inicio=None, 
                 data_fim=None, descricao=None, status='rascunho', criado_por=None, 
                 pdf_path=None, data_criacao=None):  # Adicionar data_criacao aqui
        
        self.id = id
        self.empresa_id = empresa_id
        self.numero_contrato = numero_contrato
        self.contratante_nome = contratante_nome
        self.contratante_cnpj = contratante_cnpj
        self.contratante_email = contratante_email
        self.contratante_telefone = contratante_telefone
        self.contratada_nome = contratada_nome
        self.contratada_cnpj = contratada_cnpj
        self.contratada_email = contratada_email
        self.valor = valor
        self.prazo_dias = prazo_dias
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        self.descricao = descricao
        self.status = status
        self.criado_por = criado_por
        self.pdf_path = pdf_path
        self.data_criacao = data_criacao  # Adicionar este atributo
    
    @staticmethod
    def listar_por_empresa(empresa_id, status=None):
        """Lista contratos de uma empresa"""
        db = Database()
        query = "SELECT * FROM contratos WHERE empresa_id = %s"
        params = [empresa_id]
        
        if status:
            query += " AND status = %s"
            params.append(status)
        
        query += " ORDER BY data_criacao DESC"
        
        results = db.fetch_all(query, params)
        return [Contrato(**row) for row in results] if results else []
    
    @staticmethod
    def get_by_id(contrato_id):
        """Busca contrato por ID"""
        db = Database()
        query = "SELECT * FROM contratos WHERE id = %s"
        result = db.fetch_one(query, (contrato_id,))
        if result:
            return Contrato(**result)
        return None
    
    @staticmethod
    def estatisticas(empresa_id):
        """Retorna estatísticas dos contratos"""
        db = Database()
        
        # Total de contratos
        total = db.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s", (empresa_id,))
        total = total['total'] if total else 0
        
        # Contratos ativos
        ativos = db.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'ativo'", (empresa_id,))
        ativos = ativos['total'] if ativos else 0
        
        # Valor total
        valor_total = db.fetch_one("SELECT SUM(valor) as total FROM contratos WHERE empresa_id = %s", (empresa_id,))
        valor_total = float(valor_total['total']) if valor_total and valor_total['total'] else 0
        
        # Valor médio
        media = valor_total / total if total > 0 else 0
        
        # Contratos por mês (últimos 6 meses)
        por_mes = db.fetch_all("""
            SELECT 
                DATE_FORMAT(data_criacao, '%%m/%%Y') as mes,
                COUNT(*) as quantidade,
                SUM(valor) as valor_total
            FROM contratos
            WHERE empresa_id = %s
            GROUP BY DATE_FORMAT(data_criacao, '%%m/%%Y')
            ORDER BY MIN(data_criacao) DESC
            LIMIT 6
        """, (empresa_id,))
        
        return {
            'total': total,
            'ativos': ativos,
            'total_valor': valor_total,
            'media': media,
            'por_mes': por_mes
        }