"""
Sistema de Gamificação - Reconhecimento Positivo
Foco em progresso pessoal e conquistas significativas
"""

from datetime import datetime, timedelta
from core.database import Database
from core.logging_config import logger


class Conquista:
    """Modelo de conquista/badge"""
    
    def __init__(self, id=None, chave=None, nome=None, descricao=None,
                 categoria=None, pontos=0, icone=None, cor=None, ativo=True):
        self.id = id
        self.chave = chave
        self.nome = nome
        self.descricao = descricao
        self.categoria = categoria
        self.pontos = pontos
        self.icone = icone
        self.cor = cor
        self.ativo = ativo
    
    @staticmethod
    def get_all():
        db = Database()
        results = db.fetch_all("SELECT * FROM conquistas WHERE ativo = TRUE ORDER BY pontos ASC")
        return [Conquista(**row) for row in results] if results else []
    
    @staticmethod
    def get_by_chave(chave):
        db = Database()
        result = db.fetch_one("SELECT * FROM conquistas WHERE chave = %s", (chave,))
        return Conquista(**result) if result else None
    
    @staticmethod
    def get_by_id(id):
        db = Database()
        result = db.fetch_one("SELECT * FROM conquistas WHERE id = %s", (id,))
        return Conquista(**result) if result else None
    
    @staticmethod
    def get_by_categoria(categoria):
        db = Database()
        results = db.fetch_all("SELECT * FROM conquistas WHERE categoria = %s AND ativo = TRUE ORDER BY pontos ASC", (categoria,))
        return [Conquista(**row) for row in results] if results else []


class ConquistaUsuario:
    """Conquistas conquistadas pelo usuário"""
    
    def __init__(self, id=None, usuario_id=None, conquista_id=None, data_conquista=None):
        self.id = id
        self.usuario_id = usuario_id
        self.conquista_id = conquista_id
        self.data_conquista = data_conquista or datetime.now()
    
    @staticmethod
    def desbloquear(usuario_id, conquista_chave):
        """Desbloqueia uma conquista para o usuário (se ainda não tiver)"""
        db = Database()
        
        conquista = Conquista.get_by_chave(conquista_chave)
        if not conquista:
            logger.warning(f"Conquista não encontrada: {conquista_chave}")
            return False
        
        # Verificar se já possui
        existe = db.fetch_one(
            "SELECT id FROM conquistas_usuario WHERE usuario_id = %s AND conquista_id = %s",
            (usuario_id, conquista.id)
        )
        if existe:
            return False
        
        # Desbloquear
        db.execute(
            "INSERT INTO conquistas_usuario (usuario_id, conquista_id) VALUES (%s, %s)",
            (usuario_id, conquista.id)
        )
        
        # Adicionar pontos ao histórico
        db.execute(
            "INSERT INTO pontos_historico (usuario_id, pontos, tipo, referencia_id) VALUES (%s, %s, %s, %s)",
            (usuario_id, conquista.pontos, 'conquista', conquista.id)
        )
        
        # Atualizar pontos totais do usuário
        db.execute(
            "UPDATE usuarios SET pontos_totais = pontos_totais + %s WHERE id = %s",
            (conquista.pontos, usuario_id)
        )
        
        logger.info(f"Conquista desbloqueada! Usuário {usuario_id} -> {conquista.nome}")
        
        return {
            'conquista_id': conquista.id,
            'nome': conquista.nome,
            'descricao': conquista.descricao,
            'pontos': conquista.pontos,
            'icone': conquista.icone,
            'cor': conquista.cor,
            'chave': conquista.chave
        }
    
    @staticmethod
    def listar_por_usuario(usuario_id):
        db = Database()
        query = """
            SELECT c.*, cu.data_conquista 
            FROM conquistas_usuario cu
            JOIN conquistas c ON cu.conquista_id = c.id
            WHERE cu.usuario_id = %s
            ORDER BY cu.data_conquista DESC
        """
        results = db.fetch_all(query, (usuario_id,))
        return results if results else []
    
    @staticmethod
    def contar_por_usuario(usuario_id):
        db = Database()
        result = db.fetch_one(
            "SELECT COUNT(*) as total FROM conquistas_usuario WHERE usuario_id = %s",
            (usuario_id,)
        )
        return result['total'] if result else 0
    
    @staticmethod
    def total_pontos(usuario_id):
        db = Database()
        result = db.fetch_one(
            "SELECT pontos_totais FROM usuarios WHERE id = %s",
            (usuario_id,)
        )
        return result['pontos_totais'] if result else 0
    
    @staticmethod
    def ultimas_conquistas(usuario_id, limite=5):
        db = Database()
        query = """
            SELECT c.*, cu.data_conquista 
            FROM conquistas_usuario cu
            JOIN conquistas c ON cu.conquista_id = c.id
            WHERE cu.usuario_id = %s
            ORDER BY cu.data_conquista DESC
            LIMIT %s
        """
        results = db.fetch_all(query, (usuario_id, limite))
        return results if results else []


class Nivel:
    """Sistema de níveis baseado em pontos"""
    
    @staticmethod
    def get_nivel_atual(pontos):
        db = Database()
        result = db.fetch_one(
            "SELECT * FROM niveis WHERE pontos_minimos <= %s ORDER BY nivel DESC LIMIT 1",
            (pontos,)
        )
        if result:
            return result
        return {'nivel': 1, 'pontos_minimos': 0, 'titulo': 'Aprendiz', 'icone': '🌱', 'cor': '#9ca3af'}
    
    @staticmethod
    def get_proximo_nivel(pontos):
        db = Database()
        result = db.fetch_one(
            "SELECT * FROM niveis WHERE pontos_minimos > %s ORDER BY nivel ASC LIMIT 1",
            (pontos,)
        )
        return result if result else None
    
    @staticmethod
    def get_all_niveis():
        db = Database()
        results = db.fetch_all("SELECT * FROM niveis ORDER BY nivel ASC")
        return results if results else []
    
    @staticmethod
    def progresso_para_proximo_nivel(pontos):
        atual = Nivel.get_nivel_atual(pontos)
        proximo = Nivel.get_proximo_nivel(pontos)
        
        if not proximo:
            return 100
        
        pontos_atuais = pontos - atual['pontos_minimos']
        pontos_necessarios = proximo['pontos_minimos'] - atual['pontos_minimos']
        
        if pontos_necessarios <= 0:
            return 100
        
        return round((pontos_atuais / pontos_necessarios) * 100, 1)
    
    @staticmethod
    def verificar_e_atualizar_nivel(usuario_id):
        """Verifica se usuário subiu de nível e atualiza"""
        pontos = ConquistaUsuario.total_pontos(usuario_id)
        nivel_atual_data = Nivel.get_nivel_atual(pontos)
        
        db = Database()
        usuario = db.fetch_one("SELECT nivel FROM usuarios WHERE id = %s", (usuario_id,))
        
        if usuario and usuario['nivel'] != nivel_atual_data['nivel']:
            db.execute("UPDATE usuarios SET nivel = %s WHERE id = %s", 
                      (nivel_atual_data['nivel'], usuario_id))
            return {
                'subiu_nivel': True,
                'nivel_anterior': usuario['nivel'],
                'nivel_atual': nivel_atual_data['nivel'],
                'titulo': nivel_atual_data['titulo'],
                'icone': nivel_atual_data['icone'],
                'cor': nivel_atual_data['cor']
            }
        return {'subiu_nivel': False}


class SistemaReconhecimento:
    """Sistema que dispara conquistas baseado em ações do usuário"""
    
    @staticmethod
    def verificar_conquistas_apos_contrato(contrato, usuario):
        """Verifica conquistas após criação/aprovação de contrato"""
        db = Database()
        usuario_id = usuario.id
        
        # ===== QUALIDADE =====
        
        # Primeiro contrato sem correção?
        if not getattr(contrato, 'precisou_correcao', False):
            total_acertos = db.fetch_one("""
                SELECT COUNT(*) as total FROM contratos 
                WHERE usuario_criacao_id = %s AND status = 'ativo' AND precisou_correcao = FALSE
            """, (usuario_id,))
            
            if total_acertos and total_acertos['total'] == 1:
                resultado = ConquistaUsuario.desbloquear(usuario_id, 'primeiro_acerto')
                if resultado:
                    return resultado
            
            if total_acertos and total_acertos['total'] >= 10:
                resultado = ConquistaUsuario.desbloquear(usuario_id, 'qualidade_diamante')
                if resultado:
                    return resultado
        
        # Documentação detalhada?
        observacoes = getattr(contrato, 'observacoes', None) or getattr(contrato, 'descricao', '')
        if observacoes and len(observacoes) > 100:
            total_documentados = db.fetch_one("""
                SELECT COUNT(*) as total FROM contratos 
                WHERE usuario_criacao_id = %s 
                AND (observacoes IS NOT NULL AND LENGTH(observacoes) > 100 
                     OR descricao IS NOT NULL AND LENGTH(descricao) > 100)
            """, (usuario_id,))
            
            if total_documentados and total_documentados['total'] >= 5:
                resultado = ConquistaUsuario.desbloquear(usuario_id, 'documentador')
                if resultado:
                    return resultado
        
        # ===== AGILIDADE =====
        
        # Entrega rápida (menos de 24h entre criação e envio)
        data_envio = getattr(contrato, 'data_envio_analise', None)
        data_criacao = getattr(contrato, 'data_criacao', None)
        
        if data_envio and data_criacao:
            if isinstance(data_envio, str):
                data_envio = datetime.strptime(data_envio, '%Y-%m-%d %H:%M:%S')
            if isinstance(data_criacao, str):
                data_criacao = datetime.strptime(data_criacao, '%Y-%m-%d %H:%M:%S')
                
            tempo_horas = (data_envio - data_criacao).total_seconds() / 3600
            if tempo_horas <= 24:
                entregas_rapidas = db.fetch_one("""
                    SELECT COUNT(*) as total FROM contratos 
                    WHERE usuario_criacao_id = %s 
                    AND TIMESTAMPDIFF(HOUR, data_criacao, data_envio_analise) <= 24
                """, (usuario_id,))
                
                if entregas_rapidas and entregas_rapidas['total'] == 1:
                    resultado = ConquistaUsuario.desbloquear(usuario_id, 'primeira_entrega')
                    if resultado:
                        return resultado
                
                if entregas_rapidas and entregas_rapidas['total'] >= 5:
                    resultado = ConquistaUsuario.desbloquear(usuario_id, 'consistencia_rapida')
                    if resultado:
                        return resultado
        
        # ===== CONSISTÊNCIA =====
        
        # Primeiro contrato
        total_contratos = db.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE usuario_criacao_id = %s", (usuario_id,))
        if total_contratos and total_contratos['total'] == 1:
            resultado = ConquistaUsuario.desbloquear(usuario_id, 'estreante')
            if resultado:
                return resultado
        
        if total_contratos and total_contratos['total'] >= 50:
            resultado = ConquistaUsuario.desbloquear(usuario_id, 'mestre_contratos')
            if resultado:
                return resultado
        
        # Dias trabalhados
        dias_trabalhados = db.fetch_one("""
            SELECT COUNT(DISTINCT DATE(data_criacao)) as total 
            FROM contratos WHERE usuario_criacao_id = %s
        """, (usuario_id,))
        
        if dias_trabalhados and dias_trabalhados['total'] >= 10:
            resultado = ConquistaUsuario.desbloquear(usuario_id, 'dedicado')
            if resultado:
                return resultado
        
        return None
    
    @staticmethod
    def verificar_conquistas_apos_feedback(usuario_id, sugestao):
        """Verifica conquistas após feedback valioso"""
        if sugestao and len(sugestao) > 50:
            db = Database()
            feedbacks = db.fetch_one("""
                SELECT COUNT(*) as total FROM feedbacks 
                WHERE usuario_id = %s AND LENGTH(sugestao) > 50
            """, (usuario_id,))
            
            if feedbacks and feedbacks['total'] >= 1:
                resultado = ConquistaUsuario.desbloquear(usuario_id, 'feedback_valioso')
                return resultado
        return None
    
    @staticmethod
    def verificar_e_atualizar_nivel(usuario_id):
        """Verifica se usuário subiu de nível e retorna dados para notificação"""
        return Nivel.verificar_e_atualizar_nivel(usuario_id)
    
    @staticmethod
    def atualizar_streak(usuario_id):
        """Atualiza sequência de dias consecutivos trabalhados"""
        db = Database()
        
        # Buscar último acesso
        usuario = db.fetch_one("SELECT ultimo_acesso, streak_dias FROM usuarios WHERE id = %s", (usuario_id,))
        
        hoje = datetime.now().date()
        streak_atual = usuario['streak_dias'] if usuario else 0
        
        if usuario and usuario['ultimo_acesso']:
            ultimo_acesso = usuario['ultimo_acesso']
            if isinstance(ultimo_acesso, str):
                ultimo_acesso = datetime.strptime(ultimo_acesso, '%Y-%m-%d %H:%M:%S')
            
            diferenca = (hoje - ultimo_acesso.date()).days
            
            if diferenca == 1:
                # Continuou streak
                novo_streak = streak_atual + 1
                db.execute("UPDATE usuarios SET streak_dias = %s, ultimo_acesso = NOW() WHERE id = %s", 
                          (novo_streak, usuario_id))
            elif diferenca > 1:
                # Quebrou streak
                db.execute("UPDATE usuarios SET streak_dias = 1, ultimo_acesso = NOW() WHERE id = %s", (usuario_id,))
            else:
                # Mesmo dia, não atualiza streak
                pass
        else:
            # Primeiro acesso
            db.execute("UPDATE usuarios SET streak_dias = 1, ultimo_acesso = NOW() WHERE id = %s", (usuario_id,))
        
        # Verificar conquista de streak
        novo_streak = db.fetch_one("SELECT streak_dias FROM usuarios WHERE id = %s", (usuario_id,))
        if novo_streak and novo_streak['streak_dias'] >= 10:
            ConquistaUsuario.desbloquear(usuario_id, 'dedicado')


class EstatisticasGamificacao:
    """Estatísticas para dashboards de gamificação"""
    
    @staticmethod
    def ranking_empresa(empresa_id, limite=10):
        """Ranking da empresa (apenas quem tem pontos positivos)"""
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
    def posicao_usuario(usuario_id, empresa_id):
        """Posição do usuário no ranking da empresa"""
        db = Database()
        
        pontos_usuario = ConquistaUsuario.total_pontos(usuario_id)
        
        posicao = db.fetch_one("""
            SELECT COUNT(*) + 1 as posicao FROM (
                SELECT u.id, COALESCE(u.pontos_totais, 0) as pontos
                FROM usuarios u
                WHERE u.empresa_id = %s AND u.ativo = TRUE
                GROUP BY u.id, u.pontos_totais
                HAVING pontos > %s
            ) as ranking
        """, (empresa_id, pontos_usuario))
        
        return posicao['posicao'] if posicao else 1
    
    @staticmethod
    def estatisticas_empresa(empresa_id):
        """Estatísticas gerais da empresa"""
        db = Database()
        
        stats = db.fetch_one("""
            SELECT 
                COUNT(DISTINCT cu.id) as total_conquistas,
                COUNT(DISTINCT cu.usuario_id) as usuarios_com_conquistas,
                SUM(u.pontos_totais) as total_pontos_empresa,
                AVG(u.pontos_totais) as media_pontos
            FROM usuarios u
            LEFT JOIN conquistas_usuario cu ON u.id = cu.usuario_id
            WHERE u.empresa_id = %s AND u.ativo = TRUE
        """, (empresa_id,))
        
        return stats if stats else {
            'total_conquistas': 0,
            'usuarios_com_conquistas': 0,
            'total_pontos_empresa': 0,
            'media_pontos': 0
        }