"""
Modelo de Notificações do ValidaPy
"""
from datetime import datetime
from core.database import Database
from core.logging_config import logger

class Notificacao:
    """Modelo para gerenciar notificações do sistema"""
    
    TIPOS = {
        'success': 'success',
        'danger': 'danger',
        'warning': 'warning',
        'info': 'info'
    }
    
    def __init__(self, id=None, usuario_id=None, empresa_id=None, titulo=None,
                 mensagem=None, tipo='info', lida=False, link=None,
                 data_criacao=None, data_leitura=None, remetente_nome=None,
                 usuario_acao_nome=None):  # Mantido para compatibilidade com dados antigos
        self.id = id
        self.usuario_id = usuario_id
        self.empresa_id = empresa_id
        self.titulo = titulo
        self.mensagem = mensagem
        self.tipo = tipo if tipo in self.TIPOS else 'info'
        self.lida = lida
        self.link = link
        self.data_criacao = data_criacao or datetime.now()
        self.data_leitura = data_leitura
        # Usa remetente_nome se disponível, senão usa usuario_acao_nome (para compatibilidade)
        self.remetente_nome = remetente_nome or usuario_acao_nome or 'Sistema'
    
    def save(self):
        db = Database()
        if self.id:
            query = "UPDATE notificacoes SET lida = %s, data_leitura = %s WHERE id = %s"
            db.execute(query, (self.lida, self.data_leitura, self.id))
            return self.id
        else:
            # Verifica se a coluna remetente_nome existe
            try:
                query = """
                    INSERT INTO notificacoes (usuario_id, empresa_id, titulo, mensagem, tipo, link, remetente_nome)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                self.id = db.execute_return_id(query, (
                    self.usuario_id, self.empresa_id, self.titulo,
                    self.mensagem, self.tipo, self.link, self.remetente_nome
                ))
            except:
                # Fallback para coluna antiga
                query = """
                    INSERT INTO notificacoes (usuario_id, empresa_id, titulo, mensagem, tipo, link, usuario_acao_nome)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                self.id = db.execute_return_id(query, (
                    self.usuario_id, self.empresa_id, self.titulo,
                    self.mensagem, self.tipo, self.link, self.remetente_nome
                ))
            return self.id
    
    def marcar_como_lida(self):
        self.lida = True
        self.data_leitura = datetime.now()
        self.save()
    
    @staticmethod
    def criar(usuario_id, empresa_id, titulo, mensagem, tipo='info', link=None, remetente_nome=None):
        notif = Notificacao(
            usuario_id=usuario_id,
            empresa_id=empresa_id,
            titulo=titulo,
            mensagem=mensagem,
            tipo=tipo,
            link=link,
            remetente_nome=remetente_nome
        )
        notif.save()
        logger.info(f"Notificação criada para usuário {usuario_id}: {titulo}")
        return notif
    
    @staticmethod
    def criar_para_todos_empresa(empresa_id, titulo, mensagem, tipo='info', link=None, excluir_usuario_id=None, remetente_nome=None):
        db = Database()
        query = "SELECT id FROM usuarios WHERE empresa_id = %s AND ativo = TRUE"
        params = [empresa_id]
        if excluir_usuario_id:
            query += " AND id != %s"
            params.append(excluir_usuario_id)
        
        usuarios = db.fetch_all(query, params)
        for usuario in usuarios:
            Notificacao.criar(
                usuario_id=usuario['id'],
                empresa_id=empresa_id,
                titulo=titulo,
                mensagem=mensagem,
                tipo=tipo,
                link=link,
                remetente_nome=remetente_nome
            )
    
    @staticmethod
    def criar_para_destinatario(usuario_id, empresa_id, titulo, mensagem, tipo='info', link=None, remetente_nome=None):
        return Notificacao.criar(usuario_id, empresa_id, titulo, mensagem, tipo, link, remetente_nome)
    
    @staticmethod
    def listar_por_usuario(usuario_id, apenas_nao_lidas=False, limite=50):
        db = Database()
        if apenas_nao_lidas:
            query = "SELECT * FROM notificacoes WHERE usuario_id = %s AND lida = FALSE ORDER BY data_criacao DESC LIMIT %s"
            results = db.fetch_all(query, (usuario_id, limite))
        else:
            query = "SELECT * FROM notificacoes WHERE usuario_id = %s ORDER BY data_criacao DESC LIMIT %s"
            results = db.fetch_all(query, (usuario_id, limite))
        return [Notificacao(**row) for row in results] if results else []
    
    @staticmethod
    def contar_nao_lidas(usuario_id):
        db = Database()
        result = db.fetch_one("SELECT COUNT(*) as total FROM notificacoes WHERE usuario_id = %s AND lida = FALSE", (usuario_id,))
        return result['total'] if result else 0
    
    @staticmethod
    def marcar_todas_como_lidas(usuario_id):
        db = Database()
        db.execute("UPDATE notificacoes SET lida = TRUE, data_leitura = NOW() WHERE usuario_id = %s AND lida = FALSE", (usuario_id,))
    
    def get_cor_por_tipo(self):
        cores = {
            'success': '#10b981',
            'danger': '#ef4444',
            'warning': '#f59e0b',
            'info': '#3b82f6'
        }
        return cores.get(self.tipo, '#6b7280')
    
    def get_icone_por_tipo(self):
        icones = {
            'success': 'bi-check-circle-fill',
            'danger': 'bi-x-circle-fill',
            'warning': 'bi-exclamation-triangle-fill',
            'info': 'bi-info-circle-fill'
        }
        return icones.get(self.tipo, 'bi-bell-fill')
    
    def __repr__(self):
        return f"<Notificacao {self.id}: {self.titulo}>"


class SistemaNotificacoes:
    """Sistema centralizado de notificações"""
    
    @staticmethod
    def notificar_contrato_criado(contrato, usuario):
        # Notificação para todos da empresa
        Notificacao.criar_para_todos_empresa(
            empresa_id=usuario.empresa_id,
            titulo="📄 Novo Contrato Criado",
            mensagem=f"{usuario.nome} criou o contrato {contrato.numero_contrato}. Aguardando envio para análise.",
            tipo="info",
            link=f"/contratos/{contrato.id}",
            remetente_nome=usuario.nome
        )
        
        # Notificação para o próprio criador
        Notificacao.criar_para_destinatario(
            usuario_id=usuario.id,
            empresa_id=usuario.empresa_id,
            titulo="✅ Contrato Criado com Sucesso",
            mensagem=f"Você criou o contrato {contrato.numero_contrato}. Agora você pode enviá-lo para análise.",
            tipo="success",
            link=f"/contratos/{contrato.id}",
            remetente_nome=usuario.nome
        )
    
    @staticmethod
    def notificar_contrato_enviado_analista(contrato, usuario_envio):
        # Notifica o remetente
        Notificacao.criar_para_destinatario(
            usuario_id=usuario_envio.id,
            empresa_id=usuario_envio.empresa_id,
            titulo="📤 Contrato Enviado para Análise",
            mensagem=f"Você enviou o contrato {contrato.numero_contrato} para análise. O analista irá revisar em breve.",
            tipo="success",
            link=f"/contratos/{contrato.id}",
            remetente_nome=usuario_envio.nome
        )
        
        # Notifica os analistas
        db = Database()
        analistas = db.fetch_all("SELECT id, nome FROM usuarios WHERE empresa_id = %s AND perfil = 'analista' AND ativo = TRUE", (contrato.empresa_id,))
        for analista in analistas:
            Notificacao.criar_para_destinatario(
                usuario_id=analista['id'],
                empresa_id=contrato.empresa_id,
                titulo="🔍 Novo Contrato para Análise",
                mensagem=f"{usuario_envio.nome} enviou o contrato {contrato.numero_contrato} para análise. Revise as informações e aprove ou solicite correções.",
                tipo="info",
                link=f"/contratos/{contrato.id}",
                remetente_nome=usuario_envio.nome
            )
    
    @staticmethod
    def notificar_contrato_em_analise(contrato, usuario_analista):
        Notificacao.criar_para_todos_empresa(
            empresa_id=usuario_analista.empresa_id,
            titulo="🔍 Contrato em Análise",
            mensagem=f"{usuario_analista.nome} iniciou a análise do contrato {contrato.numero_contrato}. Aguarde o resultado da avaliação.",
            tipo="warning",
            link=f"/contratos/{contrato.id}",
            remetente_nome=usuario_analista.nome,
            excluir_usuario_id=usuario_analista.id
        )
    
    @staticmethod
    def notificar_contrato_editado(contrato, usuario_editor):
        Notificacao.criar_para_todos_empresa(
            empresa_id=usuario_editor.empresa_id,
            titulo="✏️ Contrato em Edição",
            mensagem=f"{usuario_editor.nome} está editando o contrato {contrato.numero_contrato}. Acompanhe as alterações.",
            tipo="info",
            link=f"/contratos/{contrato.id}",
            remetente_nome=usuario_editor.nome,
            excluir_usuario_id=usuario_editor.id
        )
        
        Notificacao.criar_para_destinatario(
            usuario_id=usuario_editor.id,
            empresa_id=usuario_editor.empresa_id,
            titulo="✏️ Editando Contrato",
            mensagem=f"Você está editando o contrato {contrato.numero_contrato}. Não esqueça de salvar as alterações após concluir.",
            tipo="info",
            link=f"/contratos/{contrato.id}",
            remetente_nome=usuario_editor.nome
        )
    
    @staticmethod
    def notificar_contrato_enviado_gestor(contrato, usuario_analista):
        # Notifica o analista
        Notificacao.criar_para_destinatario(
            usuario_id=usuario_analista.id,
            empresa_id=usuario_analista.empresa_id,
            titulo="✅ Contrato Enviado para Aprovação",
            mensagem=f"Você enviou o contrato {contrato.numero_contrato} para aprovação do gestor. Aguarde o retorno.",
            tipo="success",
            link=f"/contratos/{contrato.id}",
            remetente_nome=usuario_analista.nome
        )
        
        # Notifica os gestores
        db = Database()
        gestores = db.fetch_all("SELECT id, nome FROM usuarios WHERE empresa_id = %s AND perfil IN ('gestor', 'admin_empresa') AND ativo = TRUE", (contrato.empresa_id,))
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
        
        # Notifica os demais
        Notificacao.criar_para_todos_empresa(
            empresa_id=contrato.empresa_id,
            titulo="📤 Contrato em Fase de Aprovação",
            mensagem=f"{usuario_analista.nome} encaminhou o contrato {contrato.numero_contrato} para aprovação final da gestão.",
            tipo="info",
            link=f"/contratos/{contrato.id}",
            remetente_nome=usuario_analista.nome,
            excluir_usuario_id=usuario_analista.id
        )
    
    @staticmethod
    def notificar_contrato_devolvido_analista(contrato, usuario_gestor, analista, motivo):
        Notificacao.criar_para_destinatario(
            usuario_id=analista.id,
            empresa_id=contrato.empresa_id,
            titulo="🔄 Contrato Devolvido para Revisão",
            mensagem=f"{usuario_gestor.nome} solicitou revisão do contrato {contrato.numero_contrato}. Motivo: {motivo}. Realize as correções necessárias.",
            tipo="warning",
            link=f"/contratos/{contrato.id}",
            remetente_nome=usuario_gestor.nome
        )
        
        Notificacao.criar_para_todos_empresa(
            empresa_id=contrato.empresa_id,
            titulo="🔄 Contrato em Revisão",
            mensagem=f"{usuario_gestor.nome} solicitou revisão do contrato {contrato.numero_contrato}. O contrato retornou para análise.",
            tipo="warning",
            link=f"/contratos/{contrato.id}",
            remetente_nome=usuario_gestor.nome,
            excluir_usuario_id=analista.id
        )
    
    @staticmethod
    def notificar_contrato_devolvido_assistente(contrato, usuario_analista, assistente, motivo):
        Notificacao.criar_para_destinatario(
            usuario_id=assistente.id,
            empresa_id=contrato.empresa_id,
            titulo="📝 Contrato para Correção",
            mensagem=f"{usuario_analista.nome} solicitou correções no contrato {contrato.numero_contrato}. Motivo: {motivo}. Realize as alterações e reenvie para análise.",
            tipo="warning",
            link=f"/contratos/{contrato.id}",
            remetente_nome=usuario_analista.nome
        )
        
        Notificacao.criar_para_todos_empresa(
            empresa_id=contrato.empresa_id,
            titulo="📝 Contrato em Correção",
            mensagem=f"{usuario_analista.nome} solicitou correções no contrato {contrato.numero_contrato}. O assistente fará as alterações necessárias.",
            tipo="warning",
            link=f"/contratos/{contrato.id}",
            remetente_nome=usuario_analista.nome,
            excluir_usuario_id=assistente.id
        )
    
    @staticmethod
    def notificar_contrato_aprovado(contrato, usuario_aprovador):
        Notificacao.criar_para_todos_empresa(
            empresa_id=contrato.empresa_id,
            titulo="🎉 Contrato Aprovado com Sucesso!",
            mensagem=f"{usuario_aprovador.nome} aprovou o contrato {contrato.numero_contrato}. O contrato está oficialmente ativo e válido.",
            tipo="success",
            link=f"/contratos/{contrato.id}",
            remetente_nome=usuario_aprovador.nome
        )
        
        Notificacao.criar_para_destinatario(
            usuario_id=usuario_aprovador.id,
            empresa_id=contrato.empresa_id,
            titulo="✅ Aprovação Realizada",
            mensagem=f"Você aprovou o contrato {contrato.numero_contrato}. O contrato agora está ativo no sistema.",
            tipo="success",
            link=f"/contratos/{contrato.id}",
            remetente_nome=usuario_aprovador.nome
        )
    
    @staticmethod
    def notificar_contrato_visualizado(contrato, usuario):
        # Só notifica outros usuários (não o próprio)
        Notificacao.criar_para_todos_empresa(
            empresa_id=usuario.empresa_id,
            titulo="👁️ Contrato Visualizado",
            mensagem=f"{usuario.nome} visualizou o contrato {contrato.numero_contrato}",
            tipo="info",
            link=f"/contratos/{contrato.id}",
            remetente_nome=usuario.nome,
            excluir_usuario_id=usuario.id
        )