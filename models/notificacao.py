from core.database import Database
from datetime import datetime
from core.logging_config import logger

class Notificacao:
    """Modelo de Notificações do Sistema"""
    
    def __init__(self, id=None, usuario_id=None, empresa_id=None, titulo=None, mensagem=None, 
                 tipo='info', link=None, lida=False, data_criacao=None, **kwargs):
        self.id = id
        self.usuario_id = usuario_id
        self.empresa_id = empresa_id
        self.titulo = titulo
        self.mensagem = mensagem
        self.tipo = tipo  # info, success, warning, danger
        self.link = link
        self.lida = lida
        self.data_criacao = data_criacao or datetime.now()
    
    @staticmethod
    def criar(usuario_id, titulo, mensagem, tipo='info', link=None, empresa_id=None):
        """Cria uma nova notificação"""
        # Se empresa_id não for fornecido, buscar do usuário
        if empresa_id is None:
            user = Database.fetch_one("SELECT empresa_id FROM usuarios WHERE id = %s", (usuario_id,))
            if user and user.get('empresa_id'):
                empresa_id = user['empresa_id']
        
        query = """
            INSERT INTO notificacoes (usuario_id, empresa_id, titulo, mensagem, tipo, link, data_criacao)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """
        params = (usuario_id, empresa_id, titulo, mensagem, tipo, link)
        
        try:
            notif_id = Database.execute_return_id(query, params)
            logger.info(f"Notificação criada: {titulo} para usuário {usuario_id}")
            return notif_id
        except Exception as e:
            logger.error(f"Erro ao criar notificação: {e}")
            return None
    
    @staticmethod
    def listar_por_usuario(usuario_id, limite=50, apenas_nao_lidas=False):
        """Lista notificações do usuário"""
        try:
            if apenas_nao_lidas:
                query = """
                    SELECT * FROM notificacoes 
                    WHERE usuario_id = %s AND lida = 0 
                    ORDER BY data_criacao DESC 
                    LIMIT %s
                """
                params = (usuario_id, limite)
            else:
                query = """
                    SELECT * FROM notificacoes 
                    WHERE usuario_id = %s 
                    ORDER BY data_criacao DESC 
                    LIMIT %s
                """
                params = (usuario_id, limite)
            
            results = Database.fetch_all(query, params)
            return [Notificacao(**row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Erro ao listar notificações: {e}")
            return []
    
    @staticmethod
    def listar_por_empresa(empresa_id, limite=50):
        """Lista notificações de uma empresa"""
        try:
            query = """
                SELECT * FROM notificacoes 
                WHERE empresa_id = %s 
                ORDER BY data_criacao DESC 
                LIMIT %s
            """
            results = Database.fetch_all(query, (empresa_id, limite))
            return [Notificacao(**row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Erro ao listar notificações da empresa: {e}")
            return []
    
    @staticmethod
    def contar_nao_lidas(usuario_id):
        """Conta notificações não lidas"""
        try:
            result = Database.fetch_one(
                "SELECT COUNT(*) as total FROM notificacoes WHERE usuario_id = %s AND lida = 0",
                (usuario_id,)
            )
            return result['total'] if result else 0
        except Exception as e:
            logger.error(f"Erro ao contar notificações não lidas: {e}")
            return 0
    
    @staticmethod
    def get_by_id(id):
        """Busca notificação por ID"""
        try:
            result = Database.fetch_one("SELECT * FROM notificacoes WHERE id = %s", (id,))
            return Notificacao(**result) if result else None
        except Exception as e:
            logger.error(f"Erro ao buscar notificação {id}: {e}")
            return None
    
    def marcar_como_lida(self):
        """Marca notificação como lida"""
        try:
            Database.execute(
                "UPDATE notificacoes SET lida = 1 WHERE id = %s",
                (self.id,)
            )
            self.lida = True
            logger.info(f"Notificação {self.id} marcada como lida")
            return True
        except Exception as e:
            logger.error(f"Erro ao marcar notificação como lida: {e}")
            return False
    
    @staticmethod
    def marcar_todas_como_lidas(usuario_id):
        """Marca todas as notificações do usuário como lidas"""
        try:
            Database.execute(
                "UPDATE notificacoes SET lida = 1 WHERE usuario_id = %s AND lida = 0",
                (usuario_id,)
            )
            logger.info(f"Todas notificações marcadas como lidas para usuário {usuario_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao marcar todas notificações como lidas: {e}")
            return False
    
    def excluir(self):
        """Exclui a notificação"""
        try:
            Database.execute("DELETE FROM notificacoes WHERE id = %s", (self.id,))
            logger.info(f"Notificação {self.id} excluída")
            return True
        except Exception as e:
            logger.error(f"Erro ao excluir notificação: {e}")
            return False
    
    @staticmethod
    def excluir_todas(usuario_id):
        """Exclui todas as notificações do usuário"""
        try:
            Database.execute("DELETE FROM notificacoes WHERE usuario_id = %s", (usuario_id,))
            logger.info(f"Todas notificações excluídas para usuário {usuario_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao excluir todas notificações: {e}")
            return False
    
    def get_icone(self):
        """Retorna o ícone baseado no tipo"""
        icones = {
            'info': 'fa-info-circle',
            'success': 'fa-check-circle',
            'warning': 'fa-exclamation-triangle',
            'danger': 'fa-times-circle'
        }
        return icones.get(self.tipo, 'fa-bell')
    
    def get_cor(self):
        """Retorna a cor baseada no tipo"""
        cores = {
            'info': '#3b82f6',
            'success': '#10b981',
            'warning': '#f59e0b',
            'danger': '#ef4444'
        }
        return cores.get(self.tipo, '#6B46C1')
    
    def to_dict(self):
        """Converte para dicionário"""
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'empresa_id': self.empresa_id,
            'titulo': self.titulo,
            'mensagem': self.mensagem,
            'tipo': self.tipo,
            'link': self.link,
            'lida': self.lida,
            'data_criacao': self.data_criacao.strftime('%d/%m/%Y %H:%M') if self.data_criacao else None,
            'icone': self.get_icone(),
            'cor': self.get_cor()
        }
    
    def __repr__(self):
        return f"<Notificacao {self.id}: {self.titulo}>"