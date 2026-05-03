# services/contrato_service.py
"""
Service de Contratos - TODAS as regras de negócio de contratos ficam aqui
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from models.contrato import Contrato
from models.usuario import Usuario
from models.empresa import Empresa
from models.notificacao import SistemaNotificacoes
from services.gamificacao_service import GamificacaoService
from core.database import Database
from core.logging_config import logger


class ContratoService:
    """Service responsável por TODAS as regras de negócio de contratos"""
    
    # ==================== CRIAÇÃO ====================
    
    @staticmethod
    def criar_contrato(
        empresa_id: int,
        usuario_id: int,
        dados: Dict[str, Any]
    ) -> Tuple[bool, Optional[Contrato], str]:
        """
        Cria um novo contrato com validações
        Regras: apenas perfis autorizados, valida dados obrigatórios
        """
        try:
            # REGRA: Verifica permissão
            usuario = Usuario.get_by_id(usuario_id)
            if not usuario or usuario.perfil not in ['assistente', 'analista', 'gestor', 'admin_empresa', 'admin_sistema']:
                return False, None, "Você não tem permissão para criar contratos"
            
            # REGRA: Valida dados obrigatórios
            if not dados.get('contratante_nome') or not dados.get('contratada_nome'):
                return False, None, "Nome do contratante e contratada são obrigatórios"
            
            # REGRA: Processa datas (se tem data_inicio e prazo, calcula data_fim)
            data_inicio = dados.get('data_inicio')
            prazo_dias = dados.get('prazo_dias')
            data_fim = dados.get('data_fim')
            
            if data_inicio and prazo_dias and not data_fim:
                if isinstance(data_inicio, str):
                    data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                else:
                    data_inicio_obj = data_inicio
                data_fim = data_inicio_obj + timedelta(days=prazo_dias)
            
            # Cria o contrato
            contrato = Contrato(
                empresa_id=empresa_id,
                contratante_nome=dados.get('contratante_nome'),
                contratante_cnpj=dados.get('contratante_cnpj'),
                contratante_email=dados.get('contratante_email'),
                contratante_telefone=dados.get('contratante_telefone'),
                contratada_nome=dados.get('contratada_nome'),
                contratada_cnpj=dados.get('contratada_cnpj'),
                contratada_email=dados.get('contratada_email'),
                valor=float(dados.get('valor', 0)),
                prazo_dias=prazo_dias,
                data_inicio=data_inicio,
                data_fim=data_fim,
                descricao=dados.get('descricao'),
                criado_por=usuario_id,
                status='rascunho'
            )
            contrato.save()
            
            # REGRA: Notifica criação
            SistemaNotificacoes.notificar_contrato_criado(contrato, usuario)
            
            # REGRA: Verifica conquistas de criação (gamificação)
            GamificacaoService.verificar_conquistas_criacao(usuario_id)
            
            logger.info(f"Contrato {contrato.numero_contrato} criado por {usuario.nome}")
            return True, contrato, "Contrato criado com sucesso!"
            
        except Exception as e:
            logger.error(f"Erro ao criar contrato: {e}")
            return False, None, f"Erro ao criar contrato: {str(e)}"
    
    # ==================== FLUXO DE APROVAÇÃO ====================
    
    @staticmethod
    def enviar_para_analista(
        contrato_id: int,
        usuario_id: int
    ) -> Tuple[bool, str]:
        """
        Envia contrato para análise (Assistente -> Analista)
        REGRAS: Apenas assistente, apenas seus contratos, apenas rascunho
        """
        try:
            contrato = Contrato.get_by_id(contrato_id)
            if not contrato:
                return False, "Contrato não encontrado"
            
            usuario = Usuario.get_by_id(usuario_id)
            if not usuario:
                return False, "Usuário não encontrado"
            
            # REGRA 1: Apenas assistente (ou admin) pode enviar
            if usuario.perfil not in ['assistente', 'admin_empresa', 'admin_sistema']:
                return False, "Apenas assistentes podem enviar contratos para análise"
            
            # REGRA 2: Só pode enviar se for o criador (ou admin)
            if usuario.perfil == 'assistente' and contrato.criado_por != usuario_id:
                return False, "Você só pode enviar seus próprios contratos"
            
            # REGRA 3: Contrato precisa estar em rascunho
            if contrato.status != 'rascunho':
                return False, f"Contrato está em {contrato.status}. Não pode ser enviado para análise"
            
            # Executa
            contrato.enviar_para_analista(usuario_id)
            
            # REGRA: Notifica
            SistemaNotificacoes.notificar_contrato_enviado_analista(contrato, usuario)
            
            # REGRA: Gamificação - verifica conquistas de agilidade
            GamificacaoService.verificar_conquistas_envio(usuario_id, contrato)
            
            logger.info(f"Contrato {contrato.numero_contrato} enviado para análise por {usuario.nome}")
            return True, "Contrato enviado para análise com sucesso!"
            
        except Exception as e:
            logger.error(f"Erro ao enviar para analista: {e}")
            return False, f"Erro: {str(e)}"
    
    @staticmethod
    def enviar_para_gestor(
        contrato_id: int,
        usuario_id: int
    ) -> Tuple[bool, str]:
        """
        Envia contrato para gestor (Analista -> Gestor)
        REGRAS: Apenas analista, contrato precisa estar em análise
        """
        try:
            contrato = Contrato.get_by_id(contrato_id)
            if not contrato:
                return False, "Contrato não encontrado"
            
            usuario = Usuario.get_by_id(usuario_id)
            if not usuario:
                return False, "Usuário não encontrado"
            
            # REGRA 1: Apenas analista (ou admin) pode enviar
            if usuario.perfil not in ['analista', 'admin_empresa', 'admin_sistema']:
                return False, "Apenas analistas podem enviar contratos para aprovação do gestor"
            
            # REGRA 2: Contrato precisa estar em análise
            if contrato.status != 'em_analise':
                return False, f"Contrato está em {contrato.status}. Deve estar 'Em Análise' para enviar ao gestor"
            
            # Executa
            contrato.enviar_para_gestor(usuario_id)
            
            # REGRA: Notifica
            SistemaNotificacoes.notificar_contrato_enviado_gestor(contrato, usuario)
            
            logger.info(f"Contrato {contrato.numero_contrato} enviado para gestor por {usuario.nome}")
            return True, "Contrato enviado para aprovação do gestor!"
            
        except Exception as e:
            logger.error(f"Erro ao enviar para gestor: {e}")
            return False, f"Erro: {str(e)}"
    
    @staticmethod
    def aprovar_contrato(
        contrato_id: int,
        usuario_id: int
    ) -> Tuple[bool, str]:
        """
        Aprova contrato (Gestor -> Ativo)
        REGRAS: Apenas gestor/admin, contrato aguardando aprovação
        """
        try:
            contrato = Contrato.get_by_id(contrato_id)
            if not contrato:
                return False, "Contrato não encontrado"
            
            usuario = Usuario.get_by_id(usuario_id)
            if not usuario:
                return False, "Usuário não encontrado"
            
            # REGRA 1: Apenas gestor ou admin podem aprovar
            if usuario.perfil not in ['gestor', 'admin_empresa', 'admin_sistema']:
                return False, "Apenas gestores ou administradores podem aprovar contratos"
            
            # REGRA 2: Contrato precisa estar aguardando aprovação
            if contrato.status != 'aguardando_aprovacao':
                return False, f"Contrato está em {contrato.status}. Deve estar 'Aguardando Aprovação'"
            
            # Executa
            contrato.aprovar(usuario_id)
            
            # REGRA: Notifica
            SistemaNotificacoes.notificar_contrato_aprovado(contrato, usuario)
            
            # REGRA: Gamificação - verifica conquistas de qualidade
            GamificacaoService.verificar_conquistas_aprovacao(usuario_id, contrato)
            
            logger.info(f"Contrato {contrato.numero_contrato} aprovado por {usuario.nome}")
            return True, "Contrato aprovado com sucesso!"
            
        except Exception as e:
            logger.error(f"Erro ao aprovar contrato: {e}")
            return False, f"Erro: {str(e)}"
    
    @staticmethod
    def devolver_para_analista(
        contrato_id: int,
        usuario_id: int,
        motivo: str
    ) -> Tuple[bool, str]:
        """
        Devolve contrato para análise (Gestor -> Analista)
        REGRAS: Apenas gestor, motivo obrigatório, contrato aguardando aprovação
        """
        try:
            # REGRA: Motivo obrigatório com mínimo de caracteres
            if not motivo or len(motivo.strip()) < 5:
                return False, "É obrigatório informar um motivo (mínimo 5 caracteres)"
            
            if len(motivo) > 500:
                return False, "Motivo muito longo (máximo 500 caracteres)"
            
            contrato = Contrato.get_by_id(contrato_id)
            if not contrato:
                return False, "Contrato não encontrado"
            
            usuario = Usuario.get_by_id(usuario_id)
            if not usuario:
                return False, "Usuário não encontrado"
            
            # REGRA: Apenas gestor ou admin podem devolver
            if usuario.perfil not in ['gestor', 'admin_empresa', 'admin_sistema']:
                return False, "Apenas gestores podem devolver contratos"
            
            # REGRA: Contrato precisa estar aguardando aprovação
            if contrato.status != 'aguardando_aprovacao':
                return False, "Apenas contratos aguardando aprovação podem ser devolvidos"
            
            # Executa
            analista = Usuario.get_by_id(contrato.atualizado_por) if contrato.atualizado_por else None
            contrato.devolver_para_analista(usuario_id, motivo)
            
            # REGRA: Notifica
            if analista:
                SistemaNotificacoes.notificar_contrato_devolvido_analista(contrato, usuario, analista, motivo)
            
            logger.info(f"Contrato {contrato.numero_contrato} devolvido para análise por {usuario.nome}. Motivo: {motivo}")
            return True, "Contrato devolvido para análise!"
            
        except Exception as e:
            logger.error(f"Erro ao devolver para analista: {e}")
            return False, f"Erro: {str(e)}"
    
    @staticmethod
    def devolver_para_assistente(
        contrato_id: int,
        usuario_id: int,
        motivo: str
    ) -> Tuple[bool, str]:
        """
        Devolve contrato para assistente (Analista -> Assistente)
        REGRAS: Apenas analista, motivo obrigatório, contrato em análise
        """
        try:
            # REGRA: Motivo obrigatório com mínimo de caracteres
            if not motivo or len(motivo.strip()) < 5:
                return False, "É obrigatório informar um motivo (mínimo 5 caracteres)"
            
            if len(motivo) > 500:
                return False, "Motivo muito longo (máximo 500 caracteres)"
            
            contrato = Contrato.get_by_id(contrato_id)
            if not contrato:
                return False, "Contrato não encontrado"
            
            usuario = Usuario.get_by_id(usuario_id)
            if not usuario:
                return False, "Usuário não encontrado"
            
            # REGRA: Apenas analista ou admin pode devolver para assistente
            if usuario.perfil not in ['analista', 'admin_empresa', 'admin_sistema']:
                return False, "Apenas analistas podem devolver contratos para assistentes"
            
            # REGRA: Contrato precisa estar em análise
            if contrato.status != 'em_analise':
                return False, "Apenas contratos em análise podem ser devolvidos"
            
            # Executa
            assistente = Usuario.get_by_id(contrato.criado_por)
            contrato.devolver_para_assistente(usuario_id, motivo)
            
            # REGRA: Notifica
            if assistente:
                SistemaNotificacoes.notificar_contrato_devolvido_assistente(contrato, usuario, assistente, motivo)
            
            logger.info(f"Contrato {contrato.numero_contrato} devolvido para assistente por {usuario.nome}")
            return True, "Contrato devolvido para o assistente!"
            
        except Exception as e:
            logger.error(f"Erro ao devolver para assistente: {e}")
            return False, f"Erro: {str(e)}"
    
    # ==================== EDIÇÃO ====================
    
    @staticmethod
    def editar_contrato(
        contrato_id: int,
        usuario_id: int,
        dados: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Edita contrato existente com validação de permissão
        REGRAS: Verifica quem pode editar baseado em perfil e status
        """
        try:
            contrato = Contrato.get_by_id(contrato_id)
            if not contrato:
                return False, "Contrato não encontrado"
            
            usuario = Usuario.get_by_id(usuario_id)
            if not usuario:
                return False, "Usuário não encontrado"
            
            # REGRAS DE PERMISSÃO PARA EDIÇÃO
            pode_editar = False
            
            if usuario.perfil in ['admin_sistema', 'admin_empresa']:
                pode_editar = True
            elif usuario.perfil == 'gestor' and contrato.status in ['rascunho', 'em_analise']:
                pode_editar = True
            elif usuario.perfil == 'analista' and contrato.status in ['rascunho', 'em_analise']:
                pode_editar = True
            elif usuario.perfil == 'assistente' and contrato.status == 'rascunho' and contrato.criado_por == usuario_id:
                pode_editar = True
            
            if not pode_editar:
                return False, "Você não tem permissão para editar este contrato"
            
            # Atualiza campos
            contrato.contratante_nome = dados.get('contratante_nome', contrato.contratante_nome)
            contrato.contratante_cnpj = dados.get('contratante_cnpj', contrato.contratante_cnpj)
            contrato.contratante_email = dados.get('contratante_email', contrato.contratante_email)
            contrato.contratante_telefone = dados.get('contratante_telefone', contrato.contratante_telefone)
            contrato.contratada_nome = dados.get('contratada_nome', contrato.contratada_nome)
            contrato.contratada_cnpj = dados.get('contratada_cnpj', contrato.contratada_cnpj)
            contrato.contratada_email = dados.get('contratada_email', contrato.contratada_email)
            contrato.valor = float(dados.get('valor', contrato.valor))
            contrato.prazo_dias = dados.get('prazo_dias', contrato.prazo_dias)
            contrato.descricao = dados.get('descricao', contrato.descricao)
            contrato.atualizado_por = usuario_id
            contrato.save()
            
            # REGRA: Notifica edição
            SistemaNotificacoes.notificar_contrato_editado(contrato, usuario)
            
            logger.info(f"Contrato {contrato.numero_contrato} editado por {usuario.nome}")
            return True, "Contrato atualizado com sucesso!"
            
        except Exception as e:
            logger.error(f"Erro ao editar contrato: {e}")
            return False, f"Erro: {str(e)}"
    
    # ==================== VISUALIZAÇÃO ====================
    
    @staticmethod
    def visualizar_contrato(
        contrato_id: int,
        usuario_id: int
    ) -> Tuple[bool, Optional[Contrato], Dict[str, Any]]:
        """
        Visualiza contrato com regras de negócio:
        - REGRA: Analista vê rascunho -> automaticamente vira 'em_analise'
        - REGRA: Notifica visualização (exceto criador em rascunho)
        """
        try:
            contrato = Contrato.get_by_id(contrato_id)
            if not contrato:
                return False, None, {'erro': 'Contrato não encontrado'}
            
            usuario = Usuario.get_by_id(usuario_id)
            if not usuario:
                return False, None, {'erro': 'Usuário não encontrado'}
            
            # REGRA: Verifica se usuário tem acesso à empresa
            if usuario.perfil != 'admin_sistema' and contrato.empresa_id != usuario.empresa_id:
                return False, None, {'erro': 'Acesso negado'}
            
            # REGRA DE NEGÓCIO: Analista que vê rascunho, transforma em análise
            transicao_ocorrida = False
            if usuario.perfil == 'analista' and contrato.status == 'rascunho':
                contrato.status = 'em_analise'
                contrato.atualizado_por = usuario_id
                contrato.save()
                SistemaNotificacoes.notificar_contrato_em_analise(contrato, usuario)
                transicao_ocorrida = True
                logger.info(f"Contrato {contrato.numero_contrato} movido para análise por visualização do analista {usuario.nome}")
            
            # REGRA: Só notifica visualização se não for criador em rascunho
            deve_notificar = not (contrato.status == 'rascunho' and contrato.criado_por == usuario_id)
            
            if deve_notificar:
                SistemaNotificacoes.notificar_contrato_visualizado(contrato, usuario)
            
            dados_retorno = {
                'transicao_ocorrida': transicao_ocorrida,
                'dias_restantes': contrato.get_dias_restantes(),
                'pdf_url': contrato.pdf_path
            }
            
            return True, contrato, dados_retorno
            
        except Exception as e:
            logger.error(f"Erro ao visualizar contrato: {e}")
            return False, None, {'erro': str(e)}
    
    # ==================== PERMISSÃO ====================
    
    @staticmethod
    def verificar_permissao_acesso(
        contrato_id: int,
        usuario_id: int
    ) -> Tuple[bool, Optional[Contrato], str]:
        """
        Verifica se o usuário tem acesso ao contrato
        """
        try:
            contrato = Contrato.get_by_id(contrato_id)
            if not contrato:
                return False, None, "Contrato não encontrado"
            
            usuario = Usuario.get_by_id(usuario_id)
            if not usuario:
                return False, None, "Usuário não encontrado"
            
            # Admin sistema vê tudo
            if usuario.perfil == 'admin_sistema':
                return True, contrato, "OK"
            
            # Verifica se pertence à mesma empresa
            if contrato.empresa_id != usuario.empresa_id:
                return False, None, "Acesso negado"
            
            return True, contrato, "OK"
            
        except Exception as e:
            logger.error(f"Erro ao verificar permissão: {e}")
            return False, None, f"Erro: {str(e)}"
    
    # ==================== CANCELAMENTO ====================
    
    @staticmethod
    def cancelar_contrato(
        contrato_id: int,
        usuario_id: int,
        motivo: str = None
    ) -> Tuple[bool, str]:
        """
        Cancela contrato (apenas admins)
        REGRAS: Apenas admin_sistema ou admin_empresa
        """
        try:
            contrato = Contrato.get_by_id(contrato_id)
            if not contrato:
                return False, "Contrato não encontrado"
            
            usuario = Usuario.get_by_id(usuario_id)
            if not usuario:
                return False, "Usuário não encontrado"
            
            # REGRA: Apenas admin pode cancelar
            if usuario.perfil not in ['admin_sistema', 'admin_empresa']:
                return False, "Apenas administradores podem cancelar contratos"
            
            # REGRA: Verifica empresa
            if usuario.perfil != 'admin_sistema' and contrato.empresa_id != usuario.empresa_id:
                return False, "Acesso negado"
            
            # Executa
            motivo = motivo or "Cancelado pelo administrador"
            contrato.cancelar(usuario_id, motivo)
            
            logger.info(f"Contrato {contrato.numero_contrato} cancelado por {usuario.nome}")
            return True, "Contrato cancelado com sucesso!"
            
        except Exception as e:
            logger.error(f"Erro ao cancelar contrato: {e}")
            return False, f"Erro: {str(e)}"
    
    # ==================== ESTATÍSTICAS ====================
    
    @staticmethod
    def get_estatisticas_contratos(
        empresa_id: int,
        usuario_perfil: str
    ) -> Tuple[bool, Dict[str, Any], str]:
        """
        Retorna estatísticas com validação de permissão
        REGRA: Apenas admin_empresa ou superior
        """
        try:
            if usuario_perfil not in ['admin_empresa', 'admin_sistema']:
                return False, {}, "Apenas administradores podem ver estatísticas"
            
            stats = Contrato.estatisticas(empresa_id)
            
            # Busca contratos por mês para gráfico
            db = Database()
            contratos_por_mes = db.fetch_all("""
                SELECT 
                    DATE_FORMAT(data_criacao, '%%Y-%%m') as mes,
                    COUNT(*) as total,
                    COALESCE(SUM(valor), 0) as valor_total
                FROM contratos
                WHERE empresa_id = %s
                GROUP BY DATE_FORMAT(data_criacao, '%%Y-%%m')
                ORDER BY mes DESC
                LIMIT 12
            """, (empresa_id,))
            
            return True, {
                'stats': stats,
                'contratos_por_mes': contratos_por_mes
            }, "OK"
            
        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas: {e}")
            return False, {}, str(e)