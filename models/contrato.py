from datetime import datetime
from core.database import Database
from core.logging_config import logger
import uuid

class Contrato:
    def __init__(self, id=None, empresa_id=None, numero_contrato=None, 
                 contratante_nome=None, contratante_cnpj=None, contratante_email=None, 
                 contratante_telefone=None, contratada_nome=None, contratada_cnpj=None, 
                 contratada_email=None, valor=None, prazo_dias=None, data_inicio=None, 
                 data_fim=None, descricao=None, status='rascunho', criado_por=None,
                 atualizado_por=None, aprovado_por=None, data_aprovacao=None,
                 solicitado_aprovacao=False, data_solicitacao=None,
                 pdf_path=None, data_criacao=None, data_atualizacao=None,
                 motivo_revisao=None, motivo_rejeicao=None):
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
        self.solicitado_aprovacao = solicitado_aprovacao
        self.data_solicitacao = data_solicitacao
        self.pdf_path = pdf_path
        self.motivo_revisao = motivo_revisao
        self.motivo_rejeicao = motivo_rejeicao
        self.data_criacao = data_criacao or datetime.now()
        self.data_atualizacao = data_atualizacao or datetime.now()
    
    @staticmethod
    def gerar_numero_contrato():
        data = datetime.now().strftime("%Y%m%d")
        codigo = str(uuid.uuid4())[:6].upper()
        return f"CT-{data}-{codigo}"
    
    def get_criador_nome(self):
        """Retorna o nome do criador do contrato"""
        if not self.criado_por:
            return 'Sistema'
        db = Database()
        result = db.fetch_one("SELECT nome FROM usuarios WHERE id = %s", (self.criado_por,))
        return result['nome'] if result else 'Usuário não encontrado'
    
    def get_aprovador_nome(self):
        """Retorna o nome do aprovador do contrato"""
        if not self.aprovado_por:
            return None
        db = Database()
        result = db.fetch_one("SELECT nome FROM usuarios WHERE id = %s", (self.aprovado_por,))
        return result['nome'] if result else None
    
    def get_info_auditoria(self):
        """Retorna informações de auditoria do contrato"""
        return {
            'criado_por_nome': self.get_criador_nome(),
            'criado_em': self.data_criacao.strftime('%d/%m/%Y %H:%M') if self.data_criacao else None,
            'atualizado_em': self.data_atualizacao.strftime('%d/%m/%Y %H:%M') if self.data_atualizacao else None,
            'aprovado_por_nome': self.get_aprovador_nome(),
            'aprovado_em': self.data_aprovacao.strftime('%d/%m/%Y %H:%M') if self.data_aprovacao else None
        }
    
    def save(self):
        db = Database()
        if self.id:
            query = """
                UPDATE contratos SET
                    contratante_nome = %s, contratante_cnpj = %s, contratante_email = %s,
                    contratante_telefone = %s, contratada_nome = %s, contratada_cnpj = %s,
                    contratada_email = %s, valor = %s, prazo_dias = %s, data_inicio = %s,
                    data_fim = %s, descricao = %s, status = %s, pdf_path = %s,
                    atualizado_por = %s, solicitado_aprovacao = %s, data_solicitacao = %s,
                    motivo_revisao = %s, motivo_rejeicao = %s,
                    data_atualizacao = NOW()
                WHERE id = %s
            """
            params = (
                self.contratante_nome, self.contratante_cnpj, self.contratante_email,
                self.contratante_telefone, self.contratada_nome, self.contratada_cnpj,
                self.contratada_email, self.valor, self.prazo_dias, self.data_inicio,
                self.data_fim, self.descricao, self.status, self.pdf_path,
                self.atualizado_por, self.solicitado_aprovacao, self.data_solicitacao,
                self.motivo_revisao, self.motivo_rejeicao, self.id
            )
            db.execute(query, params)
            return self.id
        else:
            if not self.numero_contrato:
                self.numero_contrato = self.gerar_numero_contrato()
            query = """
                INSERT INTO contratos (
                    empresa_id, numero_contrato, contratante_nome, contratante_cnpj,
                    contratante_email, contratante_telefone, contratada_nome, contratada_cnpj,
                    contratada_email, valor, prazo_dias, data_inicio, data_fim, descricao,
                    status, criado_por, pdf_path, solicitado_aprovacao
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                self.empresa_id, self.numero_contrato, self.contratante_nome, self.contratante_cnpj,
                self.contratante_email, self.contratante_telefone, self.contratada_nome, self.contratada_cnpj,
                self.contratada_email, self.valor, self.prazo_dias, self.data_inicio, self.data_fim,
                self.descricao, self.status, self.criado_por, self.pdf_path, self.solicitado_aprovacao
            )
            self.id = db.execute_return_id(query, params)
            return self.id
    
    def enviar_para_analista(self, usuario_id):
        db = Database()
        query = """
            UPDATE contratos 
            SET status = 'em_analise',
                atualizado_por = %s,
                data_atualizacao = NOW()
            WHERE id = %s
        """
        db.execute(query, (usuario_id, self.id))
        self.status = 'em_analise'
        self.atualizado_por = usuario_id
        return True
    
    def enviar_para_gestor(self, usuario_id):
        db = Database()
        query = """
            UPDATE contratos 
            SET solicitado_aprovacao = TRUE,
                status = 'aguardando_aprovacao',
                data_solicitacao = NOW(),
                atualizado_por = %s,
                data_atualizacao = NOW()
            WHERE id = %s
        """
        db.execute(query, (usuario_id, self.id))
        self.solicitado_aprovacao = True
        self.status = 'aguardando_aprovacao'
        self.data_solicitacao = datetime.now()
        self.atualizado_por = usuario_id
        return True
    
    def devolver_para_analista(self, usuario_id, motivo=None):
        db = Database()
        query = """
            UPDATE contratos 
            SET status = 'em_analise',
                solicitado_aprovacao = FALSE,
                motivo_rejeicao = %s,
                atualizado_por = %s,
                data_atualizacao = NOW()
            WHERE id = %s
        """
        db.execute(query, (motivo, usuario_id, self.id))
        self.status = 'em_analise'
        self.solicitado_aprovacao = False
        self.atualizado_por = usuario_id
        return True
    
    def devolver_para_assistente(self, usuario_id, motivo=None):
        db = Database()
        query = """
            UPDATE contratos 
            SET status = 'rascunho',
                solicitado_aprovacao = FALSE,
                motivo_revisao = %s,
                atualizado_por = %s,
                data_atualizacao = NOW()
            WHERE id = %s
        """
        db.execute(query, (motivo, usuario_id, self.id))
        self.status = 'rascunho'
        self.solicitado_aprovacao = False
        self.atualizado_por = usuario_id
        return True
    
    def aprovar(self, usuario_id):
        db = Database()
        query = """
            UPDATE contratos 
            SET status = 'ativo', 
                aprovado_por = %s,
                data_aprovacao = NOW(),
                solicitado_aprovacao = FALSE,
                data_solicitacao = NULL,
                data_atualizacao = NOW()
            WHERE id = %s
        """
        db.execute(query, (usuario_id, self.id))
        self.status = 'ativo'
        self.aprovado_por = usuario_id
        self.data_aprovacao = datetime.now()
        self.solicitado_aprovacao = False
        self.data_solicitacao = None
        return True
    
    @staticmethod
    def get_by_id(contrato_id):
        db = Database()
        result = db.fetch_one("SELECT * FROM contratos WHERE id = %s", (contrato_id,))
        return Contrato(**result) if result else None
    
    @staticmethod
    def listar_por_empresa(empresa_id, status=None):
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
                logger.error(f"Erro ao criar contrato: {e}")
                continue
        return contratos
    
    @staticmethod
    def listar_por_criador(usuario_id):
        db = Database()
        query = "SELECT * FROM contratos WHERE criado_por = %s ORDER BY data_criacao DESC"
        results = db.fetch_all(query, (usuario_id,))
        return [Contrato(**row) for row in results] if results else []
    
    @staticmethod
    def listar_pendentes_aprovacao(empresa_id=None):
        db = Database()
        if empresa_id:
            query = "SELECT * FROM contratos WHERE status = 'aguardando_aprovacao' AND empresa_id = %s ORDER BY data_solicitacao DESC"
            results = db.fetch_all(query, (empresa_id,))
        else:
            query = "SELECT * FROM contratos WHERE status = 'aguardando_aprovacao' ORDER BY data_solicitacao DESC"
            results = db.fetch_all(query)
        return [Contrato(**row) for row in results] if results else []
    
    @staticmethod
    def estatisticas(empresa_id):
        db = Database()
        total = db.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s", (empresa_id,))
        total = total['total'] if total else 0
        
        ativos = db.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'ativo'", (empresa_id,))
        ativos = ativos['total'] if ativos else 0
        
        rascunhos = db.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'rascunho'", (empresa_id,))
        rascunhos = rascunhos['total'] if rascunhos else 0
        
        em_analise = db.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'em_analise'", (empresa_id,))
        em_analise = em_analise['total'] if em_analise else 0
        
        aguardando = db.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'aguardando_aprovacao'", (empresa_id,))
        aguardando = aguardando['total'] if aguardando else 0
        
        valor_total = db.fetch_one("SELECT SUM(valor) as total FROM contratos WHERE empresa_id = %s", (empresa_id,))
        valor_total = float(valor_total['total']) if valor_total and valor_total['total'] else 0
        
        media = valor_total / total if total > 0 else 0
        
        por_mes = db.fetch_all("""
            SELECT DATE_FORMAT(data_criacao, '%%m/%%Y') as mes,
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
            'em_analise': em_analise,
            'aguardando': aguardando,
            'total_valor': valor_total,
            'media': media,
            'por_mes': por_mes
        }
    
    def __repr__(self):
        return f"<Contrato {self.id}: {self.numero_contrato}>"