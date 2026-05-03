# services/gamificacao_service.py
"""
Service de Gamificação - Regras de pontos e conquistas
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from core.database import Database
from core.logging_config import logger


class GamificacaoService:
    """Todas as regras de negócio para gamificação"""
    
    @staticmethod
    def verificar_conquistas_criacao(usuario_id: int) -> Optional[Dict]:
        """REGRA: Verifica conquistas ao criar contrato"""
        db = Database()
        
        total = db.fetch_one(
            "SELECT COUNT(*) as total FROM contratos WHERE criado_por = %s",
            (usuario_id,)
        )
        
        if total and total['total'] == 1:
            db.execute("""
                INSERT IGNORE INTO conquistas_usuario (usuario_id, conquista_id, data_conquista)
                SELECT %s, id, NOW() FROM conquistas WHERE chave = 'estreante'
            """, (usuario_id,))
            return {'conquista': 'estreante', 'mensagem': '🎉 Primeiro contrato criado!'}
        
        if total and total['total'] >= 50:
            db.execute("""
                INSERT IGNORE INTO conquistas_usuario (usuario_id, conquista_id, data_conquista)
                SELECT %s, id, NOW() FROM conquistas WHERE chave = 'mestre_contratos'
            """, (usuario_id,))
            return {'conquista': 'mestre_contratos', 'mensagem': '🏆 Mestre dos Contratos!'}
        
        return None
    
    @staticmethod
    def verificar_conquistas_envio(usuario_id: int, contrato) -> Optional[Dict]:
        """REGRA: Verifica conquistas ao enviar contrato (agilidade)"""
        db = Database()
        
        if contrato.data_criacao and contrato.data_atualizacao:
            diff = contrato.data_atualizacao - contrato.data_criacao
            if diff.total_seconds() <= 24 * 3600:
                entregas_rapidas = db.fetch_one("""
                    SELECT COUNT(*) as total FROM contratos 
                    WHERE criado_por = %s 
                    AND TIMESTAMPDIFF(HOUR, data_criacao, data_atualizacao) <= 24
                """, (usuario_id,))
                
                if entregas_rapidas and entregas_rapidas['total'] == 1:
                    db.execute("""
                        INSERT IGNORE INTO conquistas_usuario (usuario_id, conquista_id, data_conquista)
                        SELECT %s, id, NOW() FROM conquistas WHERE chave = 'primeira_entrega'
                    """, (usuario_id,))
                    return {'conquista': 'primeira_entrega', 'mensagem': '⚡ Entrega relâmpago!'}
        
        return None
    
    @staticmethod
    def verificar_conquistas_aprovacao(usuario_id: int, contrato) -> Optional[Dict]:
        """REGRA: Verifica conquistas ao aprovar contrato (qualidade)"""
        db = Database()
        
        if not getattr(contrato, 'precisou_correcao', False):
            criador_id = getattr(contrato, 'criado_por', None)
            if criador_id:
                total_acertos = db.fetch_one("""
                    SELECT COUNT(*) as total FROM contratos 
                    WHERE criado_por = %s AND status = 'ativo' AND precisou_correcao = FALSE
                """, (criador_id,))
                
                if total_acertos and total_acertos['total'] == 1:
                    db.execute("""
                        INSERT IGNORE INTO conquistas_usuario (usuario_id, conquista_id, data_conquista)
                        SELECT %s, id, NOW() FROM conquistas WHERE chave = 'primeiro_acerto'
                    """, (criador_id,))
                    return {'conquista': 'primeiro_acerto', 'mensagem': '🎯 Primeira aprovação direta!'}
        
        return None
    
    @staticmethod
    def get_ranking_empresa(empresa_id: int, limite: int = 10) -> List[Dict]:
        """REGRA: Retorna ranking da empresa por pontos"""
        db = Database()
        
        ranking = db.fetch_all("""
            SELECT 
                u.id,
                u.nome,
                u.perfil,
                COALESCE(u.pontos_totais, 0) as pontos_totais,
                COUNT(DISTINCT cu.id) as total_conquistas,
                (SELECT nivel FROM niveis WHERE pontos_minimos <= COALESCE(u.pontos_totais, 0) ORDER BY nivel DESC LIMIT 1) as nivel_atual,
                (SELECT titulo FROM niveis WHERE pontos_minimos <= COALESCE(u.pontos_totais, 0) ORDER BY nivel DESC LIMIT 1) as titulo_nivel,
                (SELECT icone FROM niveis WHERE pontos_minimos <= COALESCE(u.pontos_totais, 0) ORDER BY nivel DESC LIMIT 1) as icone_nivel,
                (SELECT cor FROM niveis WHERE pontos_minimos <= COALESCE(u.pontos_totais, 0) ORDER BY nivel DESC LIMIT 1) as cor_nivel
            FROM usuarios u
            LEFT JOIN conquistas_usuario cu ON u.id = cu.usuario_id
            WHERE u.empresa_id = %s AND u.ativo = TRUE
            GROUP BY u.id, u.nome, u.perfil, u.pontos_totais
            HAVING pontos_totais > 0 OR total_conquistas > 0
            ORDER BY pontos_totais DESC
            LIMIT %s
        """, (empresa_id, limite))
        
        return ranking if ranking else []
    
    @staticmethod
    def get_nivel_usuario(pontos: int) -> Dict:
        """REGRA: Determina o nível baseado nos pontos"""
        if pontos >= 1000:
            return {'nivel': 'Diamante', 'icone': '💎', 'cor': '#8b5cf6'}
        elif pontos >= 500:
            return {'nivel': 'Ouro', 'icone': '🥇', 'cor': '#f59e0b'}
        elif pontos >= 200:
            return {'nivel': 'Prata', 'icone': '🥈', 'cor': '#94a3b8'}
        else:
            return {'nivel': 'Bronze', 'icone': '🥉', 'cor': '#cd7f32'}