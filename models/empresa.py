# models/contrato.py
from datetime import datetime
from core.database import Database
import uuid

class Contrato:
    def __init__(self, id=None, empresa_id=None, numero_contrato=None, 
                 contratante_nome=None, contratante_cnpj=None, contratante_email=None, 
                 contratante_telefone=None, contratada_nome=None, contratada_cnpj=None, 
                 contratada_email=None, valor=None, prazo_dias=None, data_inicio=None, 
                 data_fim=None, descricao=None, status='rascunho', criado_por=None,
                 atualizado_por=None, aprovado_por=None, data_aprovacao=None,
                 pdf_path=None, data_criacao=None, data_atualizacao=None):
        """
        Inicializa um contrato com todos os campos do banco
        """
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
        self.valor = float(valor) if valor else 0
        self.prazo_dias = prazo_dias
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        self.descricao = descricao
        self.status = status
        self.criado_por = criado_por
        self.atualizado_por = atualizado_por
        self.aprovado_por = aprovado_por
        self.data_aprovacao = data_aprovacao
        self.pdf_path = pdf_path
        self.data_criacao = data_criacao
        self.data_atualizacao = data_atualizacao
    
    @staticmethod
    def gerar_numero_contrato():
        """Gera um número único para o contrato"""
        data = datetime.now().strftime("%Y%m%d")
        codigo = str(uuid.uuid4())[:6].upper()
        return f"CT-{data}-{codigo}"
    
    def save(self):
        """Salva ou atualiza o contrato no banco"""
        db = Database()
        
        if self.id:
            # Atualiza contrato existente
            query = """
                UPDATE contratos SET
                    contratante_nome = %s,
                    contratante_cnpj = %s,
                    contratante_email = %s,
                    contratante_telefone = %s,
                    contratada_nome = %s,
                    contratada_cnpj = %s,
                    contratada_email = %s,
                    valor = %s,
                    prazo_dias = %s,
                    data_inicio = %s,
                    data_fim = %s,
                    descricao = %s,
                    status = %s,
                    pdf_path = %s,
                    atualizado_por = %s,
                    data_atualizacao = NOW()
                WHERE id = %s
            """
            params = (
                self.contratante_nome, self.contratante_cnpj, self.contratante_email,
                self.contratante_telefone, self.contratada_nome, self.contratada_cnpj,
                self.contratada_email, self.valor, self.prazo_dias, self.data_inicio,
                self.data_fim, self.descricao, self.status, self.pdf_path,
                self.atualizado_por, self.id
            )
            db.execute(query, params)
            return self.id
        else:
            # Se não tiver número, gera um
            if not self.numero_contrato:
                self.numero_contrato = self.gerar_numero_contrato()
            
            # Cria novo contrato
            query = """
                INSERT INTO contratos (
                    empresa_id, numero_contrato, contratante_nome, contratante_cnpj,
                    contratante_email, contratante_telefone, contratada_nome, contratada_cnpj,
                    contratada_email, valor, prazo_dias, data_inicio, data_fim, descricao,
                    status, criado_por, pdf_path
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                self.empresa_id, self.numero_contrato, self.contratante_nome, self.contratante_cnpj,
                self.contratante_email, self.contratante_telefone, self.contratada_nome, self.contratada_cnpj,
                self.contratada_email, self.valor, self.prazo_dias, self.data_inicio, self.data_fim,
                self.descricao, self.status, self.criado_por, self.pdf_path
            )
            self.id = db.execute_return_id(query, params)
            return self.id
    
    def aprovar(self, usuario_id):
        """Método específico para aprovar contrato"""
        db = Database()
        query = """
            UPDATE contratos 
            SET status = 'ativo', 
                aprovado_por = %s,
                data_aprovacao = NOW(),
                data_atualizacao = NOW()
            WHERE id = %s
        """
        db.execute(query, (usuario_id, self.id))
        self.status = 'ativo'
        self.aprovado_por = usuario_id
        self.data_aprovacao = datetime.now()
        return True
    
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
        contratos = []
        for row in results:
            try:
                contratos.append(Contrato(**row))
            except Exception as e:
                print(f"Erro ao criar contrato: {e}")
        return contratos
    
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
        
        # Contratos em rascunho
        rascunhos = db.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'rascunho'", (empresa_id,))
        rascunhos = rascunhos['total'] if rascunhos else 0
        
        # Contratos encerrados
        encerrados = db.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'encerrado'", (empresa_id,))
        encerrados = encerrados['total'] if encerrados else 0
        
        # Contratos cancelados
        cancelados = db.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'cancelado'", (empresa_id,))
        cancelados = cancelados['total'] if cancelados else 0
        
        # Contratos suspensos
        suspensos = db.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'suspenso'", (empresa_id,))
        suspensos = suspensos['total'] if suspensos else 0
        
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
            'rascunhos': rascunhos,
            'encerrados': encerrados,
            'cancelados': cancelados,
            'suspensos': suspensos,
            'total_valor': valor_total,
            'media': media,
            'por_mes': por_mes
        }
    
    def get_criador_nome(self):
        """Retorna o nome do usuário que criou o contrato"""
        if not self.criado_por:
            return 'Sistema'
        
        db = Database()
        result = db.fetch_one("SELECT nome FROM usuarios WHERE id = %s", (self.criado_por,))
        return result['nome'] if result else 'Usuário não encontrado'
    
    def get_aprovador_nome(self):
        """Retorna o nome do usuário que aprovou o contrato"""
        if not self.aprovado_por:
            return None
        
        db = Database()
        result = db.fetch_one("SELECT nome FROM usuarios WHERE id = %s", (self.aprovado_por,))
        return result['nome'] if result else None
    
    def get_atualizador_nome(self):
        """Retorna o nome do usuário que atualizou o contrato"""
        if not self.atualizado_por:
            return None
        
        db = Database()
        result = db.fetch_one("SELECT nome FROM usuarios WHERE id = %s", (self.atualizado_por,))
        return result['nome'] if result else None
    
    def __repr__(self):
        return f"<Contrato {self.id}: {self.numero_contrato}>"