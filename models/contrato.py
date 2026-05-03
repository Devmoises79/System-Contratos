from datetime import datetime
from core.database import Database
from core.logging_config import logger
import uuid


class Contrato:
    """Modelo de Contrato com fluxo de aprovação completo"""
    
    STATUS = {
        'rascunho': 'Rascunho',
        'em_analise': 'Em Análise',
        'aguardando_aprovacao': 'Aguardando Aprovação',
        'ativo': 'Ativo',
        'encerrado': 'Encerrado',
        'cancelado': 'Cancelado'
    }
    
    def __init__(self, id=None, empresa_id=None, numero_contrato=None, 
                 contratante_nome=None, contratante_cnpj=None, contratante_email=None, 
                 contratante_telefone=None, contratada_nome=None, contratada_cnpj=None, 
                 contratada_email=None, valor=None, prazo_dias=None, data_inicio=None, 
                 data_fim=None, descricao=None, status='rascunho', criado_por=None,
                 atualizado_por=None, aprovado_por=None, data_aprovacao=None,
                 solicitado_aprovacao=False, data_solicitacao=None,
                 pdf_path=None, data_criacao=None, data_atualizacao=None,
                 motivo_revisao=None, motivo_rejeicao=None, **kwargs):
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
    
    def get_status_display(self):
        return self.STATUS.get(self.status, self.status)
    
    def get_criador_nome(self):
        if not self.criado_por:
            return 'Sistema'
        result = Database.fetch_one("SELECT nome FROM usuarios WHERE id = %s", (self.criado_por,))
        return result['nome'] if result else 'Usuário não encontrado'
    
    def get_atualizador_nome(self):
        if not self.atualizado_por:
            return None
        result = Database.fetch_one("SELECT nome FROM usuarios WHERE id = %s", (self.atualizado_por,))
        return result['nome'] if result else None
    
    def get_aprovador_nome(self):
        if not self.aprovado_por:
            return None
        result = Database.fetch_one("SELECT nome FROM usuarios WHERE id = %s", (self.aprovado_por,))
        return result['nome'] if result else None
    
    def get_info_auditoria(self):
        return {
            'criado_por_nome': self.get_criador_nome(),
            'criado_em': self.data_criacao.strftime('%d/%m/%Y %H:%M') if self.data_criacao else None,
            'atualizado_por_nome': self.get_atualizador_nome(),
            'atualizado_em': self.data_atualizacao.strftime('%d/%m/%Y %H:%M') if self.data_atualizacao else None,
            'aprovado_por_nome': self.get_aprovador_nome(),
            'aprovado_em': self.data_aprovacao.strftime('%d/%m/%Y %H:%M') if self.data_aprovacao else None
        }
    
    def get_dias_restantes(self):
        if self.data_fim and self.status == 'ativo':
            hoje = datetime.now().date()
            if isinstance(self.data_fim, str):
                data_fim = datetime.strptime(self.data_fim, '%Y-%m-%d').date()
            else:
                data_fim = self.data_fim
            dias = (data_fim - hoje).days
            return max(0, dias)
        return None
    
    def save(self):
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
                self.motivo_revisao, self.motivo_rejeicao,
                self.id
            )
            Database.execute(query, params)
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
            self.id = Database.execute_return_id(query, params)
            return self.id
    
    def enviar_para_analista(self, usuario_id):
        query = """
            UPDATE contratos 
            SET status = 'em_analise',
                solicitado_aprovacao = FALSE,
                atualizado_por = %s,
                data_atualizacao = NOW()
            WHERE id = %s
        """
        Database.execute(query, (usuario_id, self.id))
        self.status = 'em_analise'
        self.solicitado_aprovacao = False
        self.atualizado_por = usuario_id
        return True
    
    def enviar_para_gestor(self, usuario_id):
        query = """
            UPDATE contratos 
            SET solicitado_aprovacao = TRUE,
                status = 'aguardando_aprovacao',
                data_solicitacao = NOW(),
                atualizado_por = %s,
                data_atualizacao = NOW()
            WHERE id = %s
        """
        Database.execute(query, (usuario_id, self.id))
        self.solicitado_aprovacao = True
        self.status = 'aguardando_aprovacao'
        self.data_solicitacao = datetime.now()
        self.atualizado_por = usuario_id
        return True
    
    def devolver_para_analista(self, usuario_id, motivo=None):
        query = """
            UPDATE contratos 
            SET status = 'em_analise',
                solicitado_aprovacao = FALSE,
                motivo_rejeicao = %s,
                atualizado_por = %s,
                data_atualizacao = NOW()
            WHERE id = %s
        """
        Database.execute(query, (motivo, usuario_id, self.id))
        self.status = 'em_analise'
        self.solicitado_aprovacao = False
        self.motivo_rejeicao = motivo
        self.atualizado_por = usuario_id
        return True
    
    def devolver_para_assistente(self, usuario_id, motivo=None):
        query = """
            UPDATE contratos 
            SET status = 'rascunho',
                solicitado_aprovacao = FALSE,
                motivo_revisao = %s,
                atualizado_por = %s,
                data_atualizacao = NOW()
            WHERE id = %s
        """
        Database.execute(query, (motivo, usuario_id, self.id))
        self.status = 'rascunho'
        self.solicitado_aprovacao = False
        self.motivo_revisao = motivo
        self.atualizado_por = usuario_id
        return True
    
    def aprovar(self, usuario_id):
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
        Database.execute(query, (usuario_id, self.id))
        self.status = 'ativo'
        self.aprovado_por = usuario_id
        self.data_aprovacao = datetime.now()
        self.solicitado_aprovacao = False
        self.data_solicitacao = None
        return True
    
    def cancelar(self, usuario_id, motivo=None):
        query = """
            UPDATE contratos 
            SET status = 'cancelado',
                atualizado_por = %s,
                data_atualizacao = NOW()
            WHERE id = %s
        """
        Database.execute(query, (usuario_id, self.id))
        self.status = 'cancelado'
        self.atualizado_por = usuario_id
        return True
    
    def encerrar(self):
        if self.data_fim:
            hoje = datetime.now().date()
            if isinstance(self.data_fim, str):
                data_fim = datetime.strptime(self.data_fim, '%Y-%m-%d').date()
            else:
                data_fim = self.data_fim
            if hoje > data_fim:
                Database.execute("UPDATE contratos SET status = 'encerrado' WHERE id = %s", (self.id,))
                self.status = 'encerrado'
                return True
        return False
    
    def pode_editar(self, usuario_perfil, usuario_id):
        if usuario_perfil in ['admin_sistema', 'admin_empresa']:
            return True
        if usuario_perfil == 'gestor' and self.status in ['rascunho', 'em_analise']:
            return True
        if usuario_perfil == 'analista' and self.status in ['rascunho', 'em_analise']:
            return True
        if usuario_perfil == 'assistente' and self.status == 'rascunho' and self.criado_por == usuario_id:
            return True
        return False
    
    @staticmethod
    def verificar_vencimentos():
        contratos = Database.fetch_all("SELECT id, data_fim, status FROM contratos WHERE status = 'ativo'")
        encerrados = 0
        for c in contratos:
            if c['data_fim']:
                hoje = datetime.now().date()
                if isinstance(c['data_fim'], str):
                    data_fim = datetime.strptime(c['data_fim'], '%Y-%m-%d').date()
                else:
                    data_fim = c['data_fim']
                if hoje > data_fim:
                    Database.execute("UPDATE contratos SET status = 'encerrado' WHERE id = %s", (c['id'],))
                    encerrados += 1
        return encerrados
    
    @staticmethod
    def get_by_id(contrato_id):
        result = Database.fetch_one("SELECT * FROM contratos WHERE id = %s", (contrato_id,))
        return Contrato(**result) if result else None
    
    @staticmethod
    def listar_todos():
        results = Database.fetch_all("SELECT * FROM contratos ORDER BY data_criacao DESC")
        return [Contrato(**row) for row in results] if results else []
    
    @staticmethod
    def listar_por_empresa(empresa_id, status=None):
        """Lista contratos de uma empresa específica"""
        try:
            empresa_id = int(empresa_id) if empresa_id else None
            
            if not empresa_id:
                logger.warning("listar_por_empresa chamado sem empresa_id")
                return []
            
            if status:
                query = """
                    SELECT * FROM contratos 
                    WHERE empresa_id = %s AND status = %s 
                    ORDER BY id DESC
                """
                results = Database.fetch_all(query, (empresa_id, status))
            else:
                query = """
                    SELECT * FROM contratos 
                    WHERE empresa_id = %s 
                    ORDER BY id DESC
                """
                results = Database.fetch_all(query, (empresa_id,))
            
            if not results:
                return []
            
            contratos = []
            for row in results:
                try:
                    contratos.append(Contrato(**row))
                except Exception as e:
                    logger.error(f"Erro ao criar contrato: {e}")
                    continue
            
            return contratos
            
        except Exception as e:
            logger.error(f"Erro em listar_por_empresa: {e}")
            return []
    
    @staticmethod
    def listar_por_criador(usuario_id):
        """Lista contratos criados por um usuário específico"""
        try:
            results = Database.fetch_all(
                "SELECT * FROM contratos WHERE criado_por = %s ORDER BY data_criacao DESC",
                (usuario_id,)
            )
            return [Contrato(**row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Erro ao listar contratos por criador {usuario_id}: {e}")
            return []
    
    @staticmethod
    def listar_pendentes_aprovacao(empresa_id=None):
        if empresa_id:
            results = Database.fetch_all("SELECT * FROM contratos WHERE status = 'aguardando_aprovacao' AND empresa_id = %s ORDER BY data_solicitacao DESC", (empresa_id,))
        else:
            results = Database.fetch_all("SELECT * FROM contratos WHERE status = 'aguardando_aprovacao' ORDER BY data_solicitacao DESC")
        return [Contrato(**row) for row in results] if results else []
    
    @staticmethod
    def listar_em_analise(empresa_id=None):
        if empresa_id:
            results = Database.fetch_all("SELECT * FROM contratos WHERE status = 'em_analise' AND empresa_id = %s ORDER BY data_atualizacao DESC", (empresa_id,))
        else:
            results = Database.fetch_all("SELECT * FROM contratos WHERE status = 'em_analise' ORDER BY data_atualizacao DESC")
        return [Contrato(**row) for row in results] if results else []
    
    @staticmethod
    def listar_ativos(empresa_id=None):
        if empresa_id:
            results = Database.fetch_all("SELECT * FROM contratos WHERE status = 'ativo' AND empresa_id = %s ORDER BY data_inicio DESC", (empresa_id,))
        else:
            results = Database.fetch_all("SELECT * FROM contratos WHERE status = 'ativo' ORDER BY data_inicio DESC")
        return [Contrato(**row) for row in results] if results else []
    
    @staticmethod
    def estatisticas(empresa_id):
        """Calcula estatísticas da empresa"""
        try:
            total_result = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s", (empresa_id,))
            total = total_result['total'] if total_result else 0
            
            ativos_result = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'ativo'", (empresa_id,))
            ativos = ativos_result['total'] if ativos_result else 0
            
            valor_total_result = Database.fetch_one("SELECT COALESCE(SUM(valor), 0) as total FROM contratos WHERE empresa_id = %s", (empresa_id,))
            valor_total = float(valor_total_result['total']) if valor_total_result and valor_total_result['total'] else 0.0
            
            valor_total_ativos_result = Database.fetch_one("SELECT COALESCE(SUM(valor), 0) as total FROM contratos WHERE empresa_id = %s AND status = 'ativo'", (empresa_id,))
            valor_total_ativos = float(valor_total_ativos_result['total']) if valor_total_ativos_result and valor_total_ativos_result['total'] else 0.0
            
            ticket_medio = valor_total_ativos / ativos if ativos > 0 else 0.0
            
            rascunhos_result = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'rascunho'", (empresa_id,))
            rascunhos = rascunhos_result['total'] if rascunhos_result else 0
            
            em_analise_result = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'em_analise'", (empresa_id,))
            em_analise = em_analise_result['total'] if em_analise_result else 0
            
            aguardando_result = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'aguardando_aprovacao'", (empresa_id,))
            aguardando = aguardando_result['total'] if aguardando_result else 0
            
            encerrados_result = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'encerrado'", (empresa_id,))
            encerrados = encerrados_result['total'] if encerrados_result else 0
            
            cancelados_result = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'cancelado'", (empresa_id,))
            cancelados = cancelados_result['total'] if cancelados_result else 0
            
            return {
                'total': total,
                'ativos': ativos,
                'rascunhos': rascunhos,
                'em_analise': em_analise,
                'aguardando': aguardando,
                'encerrados': encerrados,
                'cancelados': cancelados,
                'total_valor': valor_total,
                'total_valor_ativos': valor_total_ativos,
                'media': ticket_medio,
                'por_mes': []
            }
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas: {e}")
            return {
                'total': 0,
                'ativos': 0,
                'rascunhos': 0,
                'em_analise': 0,
                'aguardando': 0,
                'encerrados': 0,
                'cancelados': 0,
                'total_valor': 0.0,
                'total_valor_ativos': 0.0,
                'media': 0.0,
                'por_mes': []
            }
    
    def __repr__(self):
        return f"<Contrato {self.id}: {self.numero_contrato} ({self.status})>"