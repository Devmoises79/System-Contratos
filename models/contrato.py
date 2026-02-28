# models/contrato.py
from datetime import datetime
from core.database import Database
from fpdf import FPDF
import os

class Contrato:
    def __init__(self, id=None, empresa_id=None, numero_contrato=None,
                 contratante_nome=None, contratante_cnpj=None, contratante_email=None,
                 contratante_telefone=None, contratada_nome=None, contratada_cnpj=None,
                 contratada_email=None, valor=None, prazo_dias=None, data_inicio=None,
                 data_fim=None, descricao=None, status='rascunho', criado_por=None,
                 pdf_path=None):
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
    
    @staticmethod
    def gerar_numero(empresa_id):
        """Gera número único para o contrato"""
        db = Database()
        query = "SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s"
        result = db.fetch_one(query, (empresa_id,))
        total = result['total'] + 1 if result else 1
        ano = datetime.now().year
        return f"CT-{ano}-{total:04d}"
    
    @staticmethod
    def get_by_id(contrato_id):
        db = Database()
        query = "SELECT * FROM contratos WHERE id = %s"
        result = db.fetch_one(query, (contrato_id,))
        if result:
            return Contrato(**result)
        return None
    
    @staticmethod
    def get_by_numero(empresa_id, numero):
        db = Database()
        query = "SELECT * FROM contratos WHERE empresa_id = %s AND numero_contrato = %s"
        result = db.fetch_one(query, (empresa_id, numero))
        if result:
            return Contrato(**result)
        return None
    
    @staticmethod
    def listar_por_empresa(empresa_id, status=None):
        """Lista contratos da empresa"""
        db = Database()
        query = "SELECT * FROM contratos WHERE empresa_id = %s"
        params = [empresa_id]
        
        if status:
            query += " AND status = %s"
            params.append(status)
        
        query += " ORDER BY data_criacao DESC"
        
        results = db.fetch_all(query, params)
        return [Contrato(**row) for row in results]
    
    @staticmethod
    def listar_todos():
        db = Database()
        query = "SELECT * FROM contratos ORDER BY data_criacao DESC"
        results = db.fetch_all(query)
        return [Contrato(**row) for row in results]
    
    @staticmethod
    def estatisticas(empresa_id=None):
        db = Database()
        
        if empresa_id:
            query_total = "SELECT COUNT(*) as total, SUM(valor) as total_valor FROM contratos WHERE empresa_id = %s"
            params = [empresa_id]
            result = db.fetch_one(query_total, params)
            
            query_mensal = """
                SELECT DATE_FORMAT(data_criacao, '%Y-%m') as mes, 
                       COUNT(*) as quantidade,
                       SUM(valor) as valor_total
                FROM contratos 
                WHERE empresa_id = %s
                GROUP BY DATE_FORMAT(data_criacao, '%Y-%m')
                ORDER BY mes DESC
                LIMIT 6
            """
            mensal = db.fetch_all(query_mensal, [empresa_id])
        else:
            query_total = "SELECT COUNT(*) as total, SUM(valor) as total_valor FROM contratos"
            result = db.fetch_one(query_total)
            
            query_mensal = """
                SELECT DATE_FORMAT(data_criacao, '%Y-%m') as mes, 
                       COUNT(*) as quantidade,
                       SUM(valor) as valor_total
                FROM contratos 
                GROUP BY DATE_FORMAT(data_criacao, '%Y-%m')
                ORDER BY mes DESC
                LIMIT 12
            """
            mensal = db.fetch_all(query_mensal)
        
        total = result['total'] if result else 0
        total_valor = float(result['total_valor']) if result and result['total_valor'] else 0
        
        return {
            'total': total,
            'total_valor': total_valor,
            'media': total_valor / total if total > 0 else 0,
            'por_mes': mensal
        }
    
    def save(self):
        """Salva o contrato no banco"""
        db = Database()
        
        if not self.numero_contrato:
            self.numero_contrato = self.gerar_numero(self.empresa_id)
        
        if self.id:
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
                    pdf_path = %s
                WHERE id = %s
            """
            params = (
                self.contratante_nome, self.contratante_cnpj,
                self.contratante_email, self.contratante_telefone,
                self.contratada_nome, self.contratada_cnpj,
                self.contratada_email, self.valor, self.prazo_dias,
                self.data_inicio, self.data_fim, self.descricao,
                self.status, self.pdf_path, self.id
            )
            db.execute(query, params)
            return self.id
        else:
            query = """
                INSERT INTO contratos 
                (empresa_id, numero_contrato, contratante_nome, contratante_cnpj,
                 contratante_email, contratante_telefone, contratada_nome, 
                 contratada_cnpj, contratada_email, valor, prazo_dias,
                 data_inicio, data_fim, descricao, status, criado_por)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                self.empresa_id, self.numero_contrato,
                self.contratante_nome, self.contratante_cnpj,
                self.contratante_email, self.contratante_telefone,
                self.contratada_nome, self.contratada_cnpj,
                self.contratada_email, self.valor, self.prazo_dias,
                self.data_inicio, self.data_fim, self.descricao,
                self.status, self.criado_por
            )
            self.id = db.execute_return_id(query, params)
            return self.id
    
    def gerar_pdf(self):
        """Gera PDF do contrato (seu código existente adaptado)"""
        # Cria diretório se não existir
        os.makedirs('static/uploads/contratos', exist_ok=True)
        
        pdf = FPDF()
        pdf.add_page()
        
        # Cabeçalho
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(190, 10, txt="CONTRATO DE PRESTAÇÃO DE SERVIÇOS", ln=True, align='C')
        pdf.ln(10)
        
        # Número do contrato
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(190, 10, txt=f"Contrato nº {self.numero_contrato}", ln=True, align='C')
        pdf.ln(10)
        
        # Dados do contratante
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(190, 10, txt="CONTRATANTE:", ln=True)
        pdf.set_font("Arial", '', 12)
        pdf.cell(190, 6, txt=f"Nome/Razão Social: {self.contratante_nome}", ln=True)
        pdf.cell(190, 6, txt=f"CNPJ/CPF: {self.contratante_cnpj}", ln=True)
        if self.contratante_email:
            pdf.cell(190, 6, txt=f"E-mail: {self.contratante_email}", ln=True)
        if self.contratante_telefone:
            pdf.cell(190, 6, txt=f"Telefone: {self.contratante_telefone}", ln=True)
        pdf.ln(5)
        
        # Dados da contratada
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(190, 10, txt="CONTRATADA:", ln=True)
        pdf.set_font("Arial", '', 12)
        pdf.cell(190, 6, txt=f"Nome/Razão Social: {self.contratada_nome}", ln=True)
        pdf.cell(190, 6, txt=f"CNPJ/CPF: {self.contratada_cnpj}", ln=True)
        if self.contratada_email:
            pdf.cell(190, 6, txt=f"E-mail: {self.contratada_email}", ln=True)
        pdf.ln(5)
        
        # Valores e prazos
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(190, 10, txt="VALOR E PRAZO:", ln=True)
        pdf.set_font("Arial", '', 12)
        pdf.cell(190, 6, txt=f"Valor: R$ {self.valor:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.'), ln=True)
        pdf.cell(190, 6, txt=f"Prazo: {self.prazo_dias} dias", ln=True)
        if self.data_inicio:
            pdf.cell(190, 6, txt=f"Data de início: {self.data_inicio}", ln=True)
        if self.data_fim:
            pdf.cell(190, 6, txt=f"Data de término: {self.data_fim}", ln=True)
        pdf.ln(5)
        
        # Descrição dos serviços
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(190, 10, txt="DESCRIÇÃO DOS SERVIÇOS:", ln=True)
        pdf.set_font("Arial", '', 12)
        pdf.multi_cell(190, 6, txt=self.descricao or "Não especificado")
        pdf.ln(10)
        
        # Cláusulas padrão
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(190, 10, txt="CLÁUSULAS GERAIS:", ln=True)
        pdf.set_font("Arial", '', 12)
        pdf.multi_cell(190, 6, txt="1. O contratante se obriga a pagar o valor estipulado na data do vencimento.")
        pdf.multi_cell(190, 6, txt="2. A contratada se obriga a executar os serviços conforme especificado.")
        pdf.multi_cell(190, 6, txt="3. Este contrato entra em vigor na data de sua assinatura.")
        pdf.ln(10)
        
        # Assinaturas
        pdf.ln(20)
        pdf.cell(95, 10, txt="_________________________", ln=False)
        pdf.cell(95, 10, txt="_________________________", ln=True)
        pdf.cell(95, 10, txt="Contratante", ln=False)
        pdf.cell(95, 10, txt="Contratada", ln=True)
        pdf.ln(5)
        pdf.cell(190, 6, txt=f"Local e data: ________________, ___ de ________________ de {datetime.now().year}", ln=True, align='C')
        
        # Salvar
        filename = f"contrato_{self.numero_contrato.replace('/', '_')}.pdf"
        filepath = os.path.join('static/uploads/contratos', filename)
        pdf.output(filepath)
        
        # Atualizar caminho no banco
        self.pdf_path = filepath
        db = Database()
        query = "UPDATE contratos SET pdf_path = %s WHERE id = %s"
        db.execute(query, (filepath, self.id))
        
        return filepath