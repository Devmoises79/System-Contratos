# services/notificacao_service.py
"""
Service de Notificações - Regras de negócio para envio de notificações
Centraliza todas as regras de quando e como notificar os usuários
"""
from typing import Optional, Dict, Any, List
from models.notificacao import Notificacao, SistemaNotificacoes
from models.usuario import Usuario
from models.contrato import Contrato
from core.database import Database
from core.logging_config import logger


class NotificacaoService:
    """
    Service responsável por todas as regras de negócio relacionadas a notificações
    """
    
    @staticmethod
    def criar_notificacao_contrato_criado(
        contrato: Contrato,
        usuario_criador: Usuario
    ) -> None:
        """
        REGRA: Ao criar um contrato, notificar:
        - Todos da empresa (exceto o criador)
        - O próprio criador (confirmando criação)
        """
        try:
            # REGRA: Notifica todos da empresa (exceto criador)
            SistemaNotificacoes.notificar_contrato_criado(contrato, usuario_criador)
            
            # REGRA: Notifica o criador individualmente
            Notificacao.criar_para_destinatario(
                usuario_id=usuario_criador.id,
                empresa_id=usuario_criador.empresa_id,
                titulo="✅ Contrato Criado com Sucesso",
                mensagem=f"Você criou o contrato {contrato.numero_contrato}. Agora você pode enviá-lo para análise.",
                tipo="success",
                link=f"/contratos/{contrato.id}",
                remetente_nome=usuario_criador.nome
            )
            
            logger.info(f"Notificações de criação enviadas para contrato {contrato.numero_contrato}")
            
        except Exception as e:
            logger.error(f"Erro ao criar notificações de criação: {e}")
    
    @staticmethod
    def criar_notificacao_contrato_enviado_analista(
        contrato: Contrato,
        usuario_remetente: Usuario
    ) -> None:
        """
        REGRA: Ao enviar contrato para analista:
        - Notifica o remetente (confirmação)
        - Notifica TODOS os analistas da empresa
        """
        try:
            # REGRA: Notifica o remetente
            Notificacao.criar_para_destinatario(
                usuario_id=usuario_remetente.id,
                empresa_id=usuario_remetente.empresa_id,
                titulo="📤 Contrato Enviado para Análise",
                mensagem=f"Você enviou o contrato {contrato.numero_contrato} para análise. O analista irá revisar em breve.",
                tipo="success",
                link=f"/contratos/{contrato.id}",
                remetente_nome=usuario_remetente.nome
            )
            
            # REGRA: Notifica todos os analistas da empresa
            db = Database()
            analistas = db.fetch_all("""
                SELECT id, nome FROM usuarios 
                WHERE empresa_id = %s AND perfil = 'analista' AND ativo = TRUE
            """, (contrato.empresa_id,))
            
            for analista in analistas:
                Notificacao.criar_para_destinatario(
                    usuario_id=analista['id'],
                    empresa_id=contrato.empresa_id,
                    titulo="🔍 Novo Contrato para Análise",
                    mensagem=f"{usuario_remetente.nome} enviou o contrato {contrato.numero_contrato} para análise. Revise as informações e aprove ou solicite correções.",
                    tipo="info",
                    link=f"/contratos/{contrato.id}",
                    remetente_nome=usuario_remetente.nome
                )
            
            logger.info(f"Notificações enviadas para analistas sobre contrato {contrato.numero_contrato}")
            
        except Exception as e:
            logger.error(f"Erro ao criar notificações de envio para analista: {e}")
    
    @staticmethod
    def criar_notificacao_contrato_entrou_em_analise(
        contrato: Contrato,
        usuario_analista: Usuario
    ) -> None:
        """
        REGRA: Quando um analista começa a analisar um contrato:
        - Notifica todos da empresa (exceto o analista)
        """
        try:
            SistemaNotificacoes.notificar_contrato_em_analise(contrato, usuario_analista)
            logger.info(f"Notificação de início de análise enviada para contrato {contrato.numero_contrato}")
            
        except Exception as e:
            logger.error(f"Erro ao criar notificações de início de análise: {e}")
    
    @staticmethod
    def criar_notificacao_contrato_editado(
        contrato: Contrato,
        usuario_editor: Usuario
    ) -> None:
        """
        REGRA: Quando um contrato é editado:
        - Notifica todos da empresa (exceto o editor)
        - Notifica o editor (confirmando edição)
        """
        try:
            # REGRA: Notifica todos (exceto editor)
            SistemaNotificacoes.notificar_contrato_editado(contrato, usuario_editor)
            
            # REGRA: Notifica o editor
            Notificacao.criar_para_destinatario(
                usuario_id=usuario_editor.id,
                empresa_id=usuario_editor.empresa_id,
                titulo="✏️ Contrato Editado",
                mensagem=f"Você editou o contrato {contrato.numero_contrato}. As alterações foram salvas.",
                tipo="info",
                link=f"/contratos/{contrato.id}",
                remetente_nome=usuario_editor.nome
            )
            
            logger.info(f"Notificações de edição enviadas para contrato {contrato.numero_contrato}")
            
        except Exception as e:
            logger.error(f"Erro ao criar notificações de edição: {e}")
    
    @staticmethod
    def criar_notificacao_contrato_enviado_gestor(
        contrato: Contrato,
        usuario_analista: Usuario
    ) -> None:
        """
        REGRA: Quando analista envia contrato para gestor:
        - Notifica o analista (confirmação)
        - Notifica TODOS os gestores da empresa
        - Notifica os demais (informando fase de aprovação)
        """
        try:
            # REGRA: Notifica o analista
            Notificacao.criar_para_destinatario(
                usuario_id=usuario_analista.id,
                empresa_id=usuario_analista.empresa_id,
                titulo="✅ Contrato Enviado para Aprovação",
                mensagem=f"Você enviou o contrato {contrato.numero_contrato} para aprovação do gestor. Aguarde o retorno.",
                tipo="success",
                link=f"/contratos/{contrato.id}",
                remetente_nome=usuario_analista.nome
            )
            
            # REGRA: Notifica todos os gestores e admins da empresa
            db = Database()
            gestores = db.fetch_all("""
                SELECT id, nome FROM usuarios 
                WHERE empresa_id = %s AND perfil IN ('gestor', 'admin_empresa') AND ativo = TRUE
            """, (contrato.empresa_id,))
            
            for gestor in gestores:
                Notificacao.criar_para_destinatario(
                    usuario_id=gestor['id'],
                    empresa_id=contrato.empresa_id,
                    titulo="✅ Contrato Aguardando Aprovação",
                    mensagem=f"{usuario_analista.nome} enviou o contrato {contrato.numero_contrato} para validação final. Analise e aprove o contrato.",
                    tipo="info",
                    link=f"/contratos/{contrato.id}",
                    remetente_nome=usuario_analista.nome
                )
            
            # REGRA: Notifica os demais (exceto analista e gestores)
            SistemaNotificacoes.notificar_contrato_enviado_gestor(contrato, usuario_analista)
            
            logger.info(f"Notificações de envio para gestor enviadas para contrato {contrato.numero_contrato}")
            
        except Exception as e:
            logger.error(f"Erro ao criar notificações de envio para gestor: {e}")
    
    @staticmethod
    def criar_notificacao_contrato_devolvido_analista(
        contrato: Contrato,
        usuario_gestor: Usuario,
        analista: Usuario,
        motivo: str
    ) -> None:
        """
        REGRA: Quando gestor devolve contrato para analista:
        - Notifica o analista (com motivo)
        - Notifica os demais (informando revisão)
        """
        try:
            # REGRA: Notifica o analista com o motivo
            Notificacao.criar_para_destinatario(
                usuario_id=analista.id,
                empresa_id=contrato.empresa_id,
                titulo="🔄 Contrato Devolvido para Revisão",
                mensagem=f"{usuario_gestor.nome} solicitou revisão do contrato {contrato.numero_contrato}. Motivo: {motivo}. Realize as correções necessárias.",
                tipo="warning",
                link=f"/contratos/{contrato.id}",
                remetente_nome=usuario_gestor.nome
            )
            
            # REGRA: Notifica os demais (exceto analista)
            SistemaNotificacoes.notificar_contrato_devolvido_analista(contrato, usuario_gestor, analista, motivo)
            
            logger.info(f"Notificações de devolução para analista enviadas para contrato {contrato.numero_contrato}")
            
        except Exception as e:
            logger.error(f"Erro ao criar notificações de devolução para analista: {e}")
    
    @staticmethod
    def criar_notificacao_contrato_devolvido_assistente(
        contrato: Contrato,
        usuario_analista: Usuario,
        assistente: Usuario,
        motivo: str
    ) -> None:
        """
        REGRA: Quando analista devolve contrato para assistente:
        - Notifica o assistente (com motivo)
        - Notifica os demais (informando correção)
        """
        try:
            # REGRA: Notifica o assistente com o motivo
            Notificacao.criar_para_destinatario(
                usuario_id=assistente.id,
                empresa_id=contrato.empresa_id,
                titulo="📝 Contrato para Correção",
                mensagem=f"{usuario_analista.nome} solicitou correções no contrato {contrato.numero_contrato}. Motivo: {motivo}. Realize as alterações e reenvie para análise.",
                tipo="warning",
                link=f"/contratos/{contrato.id}",
                remetente_nome=usuario_analista.nome
            )
            
            # REGRA: Notifica os demais (exceto assistente)
            SistemaNotificacoes.notificar_contrato_devolvido_assistente(contrato, usuario_analista, assistente, motivo)
            
            logger.info(f"Notificações de devolução para assistente enviadas para contrato {contrato.numero_contrato}")
            
        except Exception as e:
            logger.error(f"Erro ao criar notificações de devolução para assistente: {e}")
    
    @staticmethod
    def criar_notificacao_contrato_aprovado(
        contrato: Contrato,
        usuario_aprovador: Usuario
    ) -> None:
        """
        REGRA: Quando contrato é aprovado:
        - Notifica TODOS da empresa (comemoração)
        - Notifica o aprovador (confirmação)
        """
        try:
            # REGRA: Notifica todos da empresa
            SistemaNotificacoes.notificar_contrato_aprovado(contrato, usuario_aprovador)
            
            # REGRA: Notifica o aprovador
            Notificacao.criar_para_destinatario(
                usuario_id=usuario_aprovador.id,
                empresa_id=contrato.empresa_id,
                titulo="✅ Aprovação Realizada",
                mensagem=f"Você aprovou o contrato {contrato.numero_contrato}. O contrato agora está ativo no sistema.",
                tipo="success",
                link=f"/contratos/{contrato.id}",
                remetente_nome=usuario_aprovador.nome
            )
            
            logger.info(f"Notificações de aprovação enviadas para contrato {contrato.numero_contrato}")
            
        except Exception as e:
            logger.error(f"Erro ao criar notificações de aprovação: {e}")
    
    @staticmethod
    def criar_notificacao_contrato_visualizado(
        contrato: Contrato,
        usuario_visualizador: Usuario
    ) -> None:
        """
        REGRA: Quando contrato é visualizado:
        - Notifica todos (exceto o visualizador) - útil para auditoria
        """
        try:
            # REGRA: Não notifica se for o criador em rascunho (evita spam)
            if contrato.status == 'rascunho' and contrato.criado_por == usuario_visualizador.id:
                logger.info(f"Visualização de rascunho próprio não notificada para contrato {contrato.numero_contrato}")
                return
            
            SistemaNotificacoes.notificar_contrato_visualizado(contrato, usuario_visualizador)
            
        except Exception as e:
            logger.error(f"Erro ao criar notificações de visualização: {e}")
    
    @staticmethod
    def criar_notificacao_sistema(
        usuario_id: int,
        empresa_id: int,
        titulo: str,
        mensagem: str,
        tipo: str = 'info',
        link: Optional[str] = None
    ) -> None:
        """
        REGRA: Criar notificação genérica do sistema
        """
        try:
            Notificacao.criar_para_destinatario(
                usuario_id=usuario_id,
                empresa_id=empresa_id,
                titulo=titulo,
                mensagem=mensagem,
                tipo=tipo,
                link=link,
                remetente_nome="Sistema"
            )
            
            logger.info(f"Notificação do sistema criada para usuário {usuario_id}: {titulo}")
            
        except Exception as e:
            logger.error(f"Erro ao criar notificação do sistema: {e}")
    
    @staticmethod
    def criar_notificacao_para_multiples_usuarios(
        usuarios_ids: List[int],
        empresa_id: int,
        titulo: str,
        mensagem: str,
        tipo: str = 'info',
        link: Optional[str] = None,
        remetente_nome: str = "Sistema"
    ) -> None:
        """
        REGRA: Criar a mesma notificação para múltiplos usuários
        """
        try:
            for usuario_id in usuarios_ids:
                Notificacao.criar_para_destinatario(
                    usuario_id=usuario_id,
                    empresa_id=empresa_id,
                    titulo=titulo,
                    mensagem=mensagem,
                    tipo=tipo,
                    link=link,
                    remetente_nome=remetente_nome
                )
            
            logger.info(f"Notificação enviada para {len(usuarios_ids)} usuários: {titulo}")
            
        except Exception as e:
            logger.error(f"Erro ao criar notificações para múltiplos usuários: {e}")
    
    @staticmethod
    def limpar_notificacoes_antigas(dias: int = 90) -> int:
        """
        REGRA: Limpar notificações mais antigas que X dias
        Retorna o número de notificações removidas
        """
        try:
            from datetime import datetime, timedelta
            
            db = Database()
            data_limite = datetime.now() - timedelta(days=dias)
            
            # REGRA: Não remove notificações não lidas, apenas as lidas e antigas
            resultado = db.execute("""
                DELETE FROM notificacoes 
                WHERE lida = TRUE AND data_criacao < %s
            """, (data_limite,))
            
            # O número de linhas afetadas pode variar conforme o driver
            removidas = getattr(resultado, 'rowcount', 0)
            
            logger.info(f"Limpeza automática: {removidas} notificações antigas removidas")
            return removidas
            
        except Exception as e:
            logger.error(f"Erro ao limpar notificações antigas: {e}")
            return 0