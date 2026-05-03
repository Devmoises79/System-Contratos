# models/gamificacao.py
"""
Módulo de Gamificação - Pontuação e Rankings
"""
from datetime import datetime, timedelta
from core.database import Database
from core.logging_config import logger


class Gamificacao:
    """Modelo de gamificação para gestão de pontos e conquistas"""
    
    # Constantes de pontuação
    PONTOS_POR_CONTRATO_CRIADO = 10
    PONTOS_POR_CONTRATO_APROVADO = 50
    PONTOS_POR_CONTRATO_REJEITADO = -5
    PONTOS_POR_CONTRATO_EDITADO = 2
    PONTOS_POR_DASHBOARD_ACESSADO = 1
    PONTOS_POR_CLIENTE_CADASTRADO = 15
    PONTOS_POR_AVALIACAO_POSITIVA = 20
    
    # Níveis e pontuação necessária
    NIVEIS = {
        1: {'nome': 'Iniciante', 'pontos_min': 0},
        2: {'nome': 'Aprendiz', 'pontos_min': 100},
        3: {'nome': 'Intermediário', 'pontos_min': 300},
        4: {'nome': 'Avançado', 'pontos_min': 600},
        5: {'nome': 'Especialista', 'pontos_min': 1000},
        6: {'nome': 'Mestre', 'pontos_min': 1500},
        7: {'nome': 'Lendário', 'pontos_min': 2500}
    }
    
    @staticmethod
    def adicionar_pontos(usuario_id, acao, valor_adicional=0, metadata=None):
        """
        Adiciona pontos para um usuário baseado na ação
        
        Args:
            usuario_id: ID do usuário
            acao: Tipo de ação (ex: 'criar_contrato', 'aprovar_contrato')
            valor_adicional: Valor extra para cálculo (ex: valor do contrato)
            metadata: Informações adicionais
        """
        # Definir pontuação baseada na ação
        pontos = 0
        
        if acao == 'criar_contrato':
            pontos = Gamificacao.PONTOS_POR_CONTRATO_CRIADO
        elif acao == 'aprovar_contrato':
            pontos = Gamificacao.PONTOS_POR_CONTRATO_APROVADO
        elif acao == 'rejeitar_contrato':
            pontos = Gamificacao.PONTOS_POR_CONTRATO_REJEITADO
        elif acao == 'editar_contrato':
            pontos = Gamificacao.PONTOS_POR_CONTRATO_EDITADO
        elif acao == 'acessar_dashboard':
            pontos = Gamificacao.PONTOS_POR_DASHBOARD_ACESSADO
        elif acao == 'cadastrar_cliente':
            pontos = Gamificacao.PONTOS_POR_CLIENTE_CADASTRADO
        elif acao == 'avaliacao_positiva':
            pontos = Gamificacao.PONTOS_POR_AVALIACAO_POSITIVA
        elif acao == 'bônus_valor':
            # Bônus baseado no valor do contrato (1 ponto a cada R$ 10.000)
            pontos = int(valor_adicional / 10000) if valor_adicional else 0
        else:
            logger.warning(f"Ação desconhecida para gamificação: {acao}")
            return 0
        
        if pontos == 0:
            return 0
        
        # Verificar limite diário para ações repetitivas
        if acao in ['acessar_dashboard']:
            # Limitar acessos ao dashboard (máximo 5 pontos por dia)
            hoje = datetime.now().date()
            query = """
                SELECT SUM(pontos) as total FROM pontos_historico 
                WHERE usuario_id = %s AND acao = %s AND DATE(data_criacao) = %s
            """
            result = Database.fetch_one(query, (usuario_id, acao, hoje))
            total_hoje = result['total'] if result and result['total'] else 0
            
            if total_hoje >= 5:
                logger.debug(f"Limite diário atingido para {acao} do usuário {usuario_id}")
                return 0
        
        # Salvar no histórico
        query = """
            INSERT INTO pontos_historico (usuario_id, pontos, acao, metadata, data_criacao)
            VALUES (%s, %s, %s, %s, NOW())
        """
        import json
        metadata_str = json.dumps(metadata) if metadata else None
        Database.execute(query, (usuario_id, pontos, acao, metadata_str))
        
        # Atualizar pontuação total do usuário
        Gamificacao._atualizar_pontuacao_total(usuario_id)
        
        logger.info(f"✅ +{pontos} pontos para usuário {usuario_id} - Ação: {acao}")
        
        return pontos
    
    @staticmethod
    def _atualizar_pontuacao_total(usuario_id):
        """Atualiza a pontuação total do usuário"""
        query = """
            SELECT SUM(pontos) as total FROM pontos_historico 
            WHERE usuario_id = %s
        """
        result = Database.fetch_one(query, (usuario_id,))
        total = result['total'] if result and result['total'] else 0
        
        # Verificar se já existe registro
        query = "SELECT id FROM pontuacoes_usuarios WHERE usuario_id = %s"
        existing = Database.fetch_one(query, (usuario_id,))
        
        if existing:
            query = """
                UPDATE pontuacoes_usuarios 
                SET pontos_totais = %s, data_atualizacao = NOW()
                WHERE usuario_id = %s
            """
            Database.execute(query, (total, usuario_id))
        else:
            query = """
                INSERT INTO pontuacoes_usuarios (usuario_id, pontos_totais, nivel, data_atualizacao)
                VALUES (%s, %s, %s, NOW())
            """
            nivel = Gamificacao.get_nivel(total)
            Database.execute(query, (usuario_id, total, nivel))
        
        return total
    
    @staticmethod
    def get_pontos_usuario(usuario_id):
        """Retorna a pontuação total de um usuário"""
        query = """
            SELECT pontos_totais, nivel FROM pontuacoes_usuarios 
            WHERE usuario_id = %s
        """
        result = Database.fetch_one(query, (usuario_id,))
        
        if result:
            return result['pontos_totais'], result['nivel']
        
        return 0, 1
    
    @staticmethod
    def get_nivel(pontos):
        """Retorna o nível baseado na pontuação"""
        nivel = 1
        for n, info in sorted(Gamificacao.NIVEIS.items()):
            if pontos >= info['pontos_min']:
                nivel = n
            else:
                break
        return nivel
    
    @staticmethod
    def get_nivel_info(nivel):
        """Retorna informações do nível"""
        return Gamificacao.NIVEIS.get(nivel, Gamificacao.NIVEIS[1])
    
    @staticmethod
    def get_ranking(empresa_id=None, limite=10):
        """Retorna o ranking de usuários"""
        if empresa_id:
            query = """
                SELECT u.id, u.nome, u.email, u.perfil,
                       COALESCE(pu.pontos_totais, 0) as pontos,
                       COALESCE(pu.nivel, 1) as nivel
                FROM usuarios u
                LEFT JOIN pontuacoes_usuarios pu ON u.id = pu.usuario_id
                WHERE u.empresa_id = %s AND u.ativo = 1
                ORDER BY pontos DESC
                LIMIT %s
            """
            results = Database.fetch_all(query, (empresa_id, limite))
        else:
            query = """
                SELECT u.id, u.nome, u.email, u.perfil, u.empresa_id,
                       COALESCE(pu.pontos_totais, 0) as pontos,
                       COALESCE(pu.nivel, 1) as nivel
                FROM usuarios u
                LEFT JOIN pontuacoes_usuarios pu ON u.id = pu.usuario_id
                WHERE u.ativo = 1
                ORDER BY pontos DESC
                LIMIT %s
            """
            results = Database.fetch_all(query, (limite,))
        
        return results if results else []
    
    @staticmethod
    def get_historico_pontos(usuario_id, limite=20):
        """Retorna histórico de pontos do usuário"""
        query = """
            SELECT id, pontos, acao, metadata, data_criacao,
                   DATE_FORMAT(data_criacao, '%d/%m/%Y %H:%i') as data_formatada
            FROM pontos_historico
            WHERE usuario_id = %s
            ORDER BY data_criacao DESC
            LIMIT %s
        """
        results = Database.fetch_all(query, (usuario_id, limite))
        
        # Processar metadata JSON
        import json
        for result in results or []:
            if result.get('metadata'):
                try:
                    result['metadata'] = json.loads(result['metadata'])
                except:
                    result['metadata'] = None
        
        return results if results else []
    
    @staticmethod
    def get_estatisticas_equipe(empresa_id):
        """Retorna estatísticas de gamificação da equipe"""
        query = """
            SELECT 
                COUNT(DISTINCT u.id) as total_usuarios,
                COALESCE(SUM(pu.pontos_totais), 0) as pontos_totais_equipe,
                COALESCE(AVG(pu.pontos_totais), 0) as media_pontos,
                MAX(COALESCE(pu.pontos_totais, 0)) as maior_pontuacao,
                u.nome as usuario_destaque
            FROM usuarios u
            LEFT JOIN pontuacoes_usuarios pu ON u.id = pu.usuario_id
            WHERE u.empresa_id = %s AND u.ativo = 1
            GROUP BY u.empresa_id
        """
        result = Database.fetch_one(query, (empresa_id,))
        
        if not result:
            return {
                'total_usuarios': 0,
                'pontos_totais_equipe': 0,
                'media_pontos': 0,
                'maior_pontuacao': 0,
                'usuario_destaque': None
            }
        
        # Buscar nome do usuário destaque
        if result.get('maior_pontuacao', 0) > 0:
            query_destaque = """
                SELECT u.nome
                FROM usuarios u
                LEFT JOIN pontuacoes_usuarios pu ON u.id = pu.usuario_id
                WHERE u.empresa_id = %s AND pu.pontos_totais = %s
                LIMIT 1
            """
            destaque = Database.fetch_one(query_destaque, (empresa_id, result['maior_pontuacao']))
            if destaque:
                result['usuario_destaque'] = destaque['nome']
        
        return result
    
    @staticmethod
    def get_proximo_nivel(pontos_atual):
        """Retorna informações do próximo nível"""
        nivel_atual = Gamificacao.get_nivel(pontos_atual)
        
        if nivel_atual >= max(Gamificacao.NIVEIS.keys()):
            return {
                'nivel': nivel_atual,
                'pontos_necessarios': 0,
                'pontos_faltando': 0,
                'is_maximo': True
            }
        
        proximo_nivel = nivel_atual + 1
        pontos_necessarios = Gamificacao.NIVEIS[proximo_nivel]['pontos_min']
        pontos_faltando = pontos_necessarios - pontos_atual
        
        return {
            'nivel_atual': nivel_atual,
            'proximo_nivel': proximo_nivel,
            'pontos_necessarios': pontos_necessarios,
            'pontos_faltando': max(0, pontos_faltando),
            'is_maximo': False
        }


class PontuacaoUsuario:
    """Classe auxiliar para manipular pontuação de um usuário específico"""
    
    def __init__(self, usuario_id):
        self.usuario_id = usuario_id
        self._pontos = None
        self._nivel = None
        self._carregar_pontos()
    
    def _carregar_pontos(self):
        """Carrega pontos e nível do usuário"""
        query = """
            SELECT pontos_totais, nivel FROM pontuacoes_usuarios 
            WHERE usuario_id = %s
        """
        result = Database.fetch_one(query, (self.usuario_id,))
        
        if result:
            self._pontos = result['pontos_totais']
            self._nivel = result['nivel']
        else:
            self._pontos = 0
            self._nivel = 1
    
    @property
    def pontos(self):
        return self._pontos
    
    @property
    def nivel(self):
        return self._nivel
    
    @property
    def proximo_nivel_info(self):
        return Gamificacao.get_proximo_nivel(self._pontos)
    
    def adicionar(self, acao, valor_adicional=0, metadata=None):
        """Adiciona pontos para este usuário"""
        return Gamificacao.adicionar_pontos(self.usuario_id, acao, valor_adicional, metadata)
    
    def get_historico(self, limite=20):
        """Retorna histórico do usuário"""
        return Gamificacao.get_historico_pontos(self.usuario_id, limite)
    
    def get_info(self):
        """Retorna todas as informações do usuário"""
        return {
            'usuario_id': self.usuario_id,
            'pontos': self._pontos,
            'nivel': self._nivel,
            'nivel_info': Gamificacao.get_nivel_info(self._nivel),
            'proximo_nivel': self.proximo_nivel_info
        }