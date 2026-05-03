# analytics/contratos.py
"""
Análise de Contratos para Intermediação B2B
- Tempo médio de aprovação (SLA)
- Gargalos no processo
- Alertas de renovação
"""

from datetime import datetime
from core.database import Database
from core.logging_config import logger


class AnalyticsContratos:
    """Métricas e análises para gestão de contratos"""
    
    @staticmethod
    def alertas_vencimento(empresa_id):
        """
        Contratos que vencem nos próximos 30/60/90 dias
        Essencial para retenção de clientes
        """
        hoje = datetime.now().date()
        db = Database()
        
        alertas = {
            '30_dias': [],
            '60_dias': [],
            '90_dias': []
        }
        
        contratos = db.fetch_all("""
            SELECT id, numero_contrato, contratante_nome, 
                   contratante_cnpj, data_fim, valor, status
            FROM contratos 
            WHERE empresa_id = %s 
              AND status = 'ativo' 
              AND data_fim IS NOT NULL
            ORDER BY data_fim ASC
        """, (empresa_id,))
        
        for c in contratos:
            data_fim = c['data_fim']
            if isinstance(data_fim, str):
                data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            
            dias_restantes = (data_fim - hoje).days
            
            if 0 <= dias_restantes <= 30:
                c['dias_restantes'] = dias_restantes
                c['data_fim_str'] = data_fim.strftime('%d/%m/%Y')
                alertas['30_dias'].append(c)
            elif 31 <= dias_restantes <= 60:
                c['dias_restantes'] = dias_restantes
                c['data_fim_str'] = data_fim.strftime('%d/%m/%Y')
                alertas['60_dias'].append(c)
            elif 61 <= dias_restantes <= 90:
                c['dias_restantes'] = dias_restantes
                c['data_fim_str'] = data_fim.strftime('%d/%m/%Y')
                alertas['90_dias'].append(c)
        
        # Adiciona totais
        alertas['totais'] = {
            '30_dias': len(alertas['30_dias']),
            '60_dias': len(alertas['60_dias']),
            '90_dias': len(alertas['90_dias']),
            'total': len(alertas['30_dias']) + len(alertas['60_dias']) + len(alertas['90_dias'])
        }
        
        return alertas
    
    @staticmethod
    def tempo_medio_aprovacao(empresa_id):
        """
        Calcula o tempo médio entre criação e aprovação do contrato
        Indicador chave de eficiência (SLA)
        """
        db = Database()
        
        resultado = db.fetch_one("""
            SELECT 
                AVG(TIMESTAMPDIFF(HOUR, data_criacao, data_aprovacao)) as media_horas,
                MIN(TIMESTAMPDIFF(HOUR, data_criacao, data_aprovacao)) as min_horas,
                MAX(TIMESTAMPDIFF(HOUR, data_criacao, data_aprovacao)) as max_horas,
                COUNT(*) as total_aprovados
            FROM contratos
            WHERE empresa_id = %s 
              AND status = 'ativo'
              AND data_aprovacao IS NOT NULL
        """, (empresa_id,))
        
        media_horas = resultado['media_horas'] if resultado and resultado['media_horas'] else 0
        min_horas = resultado['min_horas'] if resultado and resultado['min_horas'] else 0
        max_horas = resultado['max_horas'] if resultado and resultado['max_horas'] else 0
        total_aprovados = resultado['total_aprovados'] if resultado else 0
        
        # Define status baseado em SLA
        # Bom: < 48h (2 dias), Atenção: 48-120h (2-5 dias), Crítico: > 120h (5+ dias)
        if media_horas < 48:
            status = 'bom'
            status_texto = '✅ Dentro do SLA'
            status_cor = 'success'
        elif media_horas < 120:
            status = 'atencao'
            status_texto = '⚠️ Acima do ideal'
            status_cor = 'warning'
        else:
            status = 'critico'
            status_texto = '🔴 Crítico'
            status_cor = 'danger'
        
        return {
            'media_horas': round(media_horas, 1),
            'media_dias': round(media_horas / 24, 1),
            'min_horas': round(min_horas, 1),
            'max_horas': round(max_horas, 1),
            'total_aprovados': total_aprovados,
            'status': status,
            'status_texto': status_texto,
            'status_cor': status_cor
        }
    
    @staticmethod
    def gargalos_processo(empresa_id, dias_parado=7):
        """
        Identifica contratos parados há mais de X dias em cada etapa
        Ajuda a diagnosticar onde o processo está travando
        """
        db = Database()
        
        # Busca contratos parados por status
        gargalos = db.fetch_all("""
            SELECT 
                status,
                COUNT(*) as quantidade,
                SUM(valor) as valor_total
            FROM contratos
            WHERE empresa_id = %s
              AND status IN ('rascunho', 'em_analise', 'aguardando_aprovacao')
              AND data_atualizacao < DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY status
        """, (empresa_id, dias_parado))
        
        # Inicializa estrutura
        resultado = {
            'rascunho': {'quantidade': 0, 'valor': 0},
            'em_analise': {'quantidade': 0, 'valor': 0},
            'aguardando_aprovacao': {'quantidade': 0, 'valor': 0},
            'dias_limite': dias_parado
        }
        
        for item in gargalos:
            status = item['status']
            if status in resultado:
                resultado[status]['quantidade'] = item['quantidade']
                resultado[status]['valor'] = float(item['valor_total']) if item['valor_total'] else 0
        
        resultado['total_contratos'] = (
            resultado['rascunho']['quantidade'] + 
            resultado['em_analise']['quantidade'] + 
            resultado['aguardando_aprovacao']['quantidade']
        )
        
        resultado['total_valor'] = (
            resultado['rascunho']['valor'] + 
            resultado['em_analise']['valor'] + 
            resultado['aguardando_aprovacao']['valor']
        )
        
        return resultado
    
    @staticmethod
    def estatisticas_gerais(empresa_id):
        """
        Métricas gerais da empresa para o dashboard
        """
        db = Database()
        
        # Total de contratos por status
        status_count = db.fetch_all("""
            SELECT status, COUNT(*) as total
            FROM contratos
            WHERE empresa_id = %s
            GROUP BY status
        """, (empresa_id,))
        
        stats = {
            'total': 0,
            'rascunho': 0,
            'em_analise': 0,
            'aguardando_aprovacao': 0,
            'ativo': 0,
            'encerrado': 0
        }
        
        for item in status_count:
            if item['status'] in stats:
                stats[item['status']] = item['total']
            stats['total'] += item['total']
        
        # Valor total contratado (ativos)
        valor_ativos = db.fetch_one("""
            SELECT SUM(valor) as total
            FROM contratos
            WHERE empresa_id = %s AND status = 'ativo'
        """, (empresa_id,))
        
        stats['valor_ativos'] = float(valor_ativos['total']) if valor_ativos and valor_ativos['total'] else 0
        
        # Contratos em aberto (não finalizados)
        stats['total_aberto'] = stats['rascunho'] + stats['em_analise'] + stats['aguardando_aprovacao']
        
        return stats
    
    @staticmethod
    def contratos_pendentes_aprovacao(empresa_id, limite=20):
        """
        Lista contratos aguardando aprovação com detalhes
        """
        db = Database()
        
        contratos = db.fetch_all("""
            SELECT c.*, u.nome as criador_nome
            FROM contratos c
            LEFT JOIN usuarios u ON c.criado_por = u.id
            WHERE c.empresa_id = %s 
              AND c.status = 'aguardando_aprovacao'
            ORDER BY c.data_solicitacao ASC
            LIMIT %s
        """, (empresa_id, limite))
        
        # Processa datas para exibição
        for c in contratos:
            if c.get('data_solicitacao'):
                data_solicitacao = c['data_solicitacao']
                if isinstance(data_solicitacao, str):
                    data_solicitacao = datetime.strptime(data_solicitacao, '%Y-%m-%d %H:%M:%S')
                c['data_solicitacao_str'] = data_solicitacao.strftime('%d/%m/%Y')
                c['dias_espera'] = (datetime.now() - data_solicitacao).days
        
        return contratos