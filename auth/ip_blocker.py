# auth/ip_blocker.py
from datetime import datetime, timedelta
from flask import request
from core.database import Database
from config import Config

class IPBlocker:
    """Sistema de bloqueio de IPs após múltiplas tentativas"""
    
    @staticmethod
    def registrar_tentativa(ip_address, email=None, sucesso=False):
        """Registra uma tentativa de login"""
        db = Database()
        query = """
            INSERT INTO tentativas_login (ip_address, email_utilizado, sucesso)
            VALUES (%s, %s, %s)
        """
        db.execute(query, (ip_address, email, sucesso))
    
    @staticmethod
    def verificar_bloqueio(ip_address):
        """Verifica se um IP está bloqueado"""
        db = Database()
        
        query = """
            SELECT * FROM ips_bloqueados 
            WHERE ip_address = %s AND ativo = TRUE AND expira_em > NOW()
        """
        bloqueado = db.fetch_one(query, (ip_address,))
        
        if bloqueado:
            agora = datetime.now()
            expira = bloqueado['expira_em']
            minutos_restantes = int((expira - agora).total_seconds() / 60)
            return True, minutos_restantes
        
        return False, 0
    
    @staticmethod
    def processar_tentativa_falha(ip_address, email=None):
        """Processa uma tentativa falha e bloqueia se necessário"""
        db = Database()
        
        # Registra a tentativa
        IPBlocker.registrar_tentativa(ip_address, email, False)
        
        # Conta tentativas nos últimos 30 minutos
        query = """
            SELECT COUNT(*) as tentativas FROM tentativas_login
            WHERE ip_address = %s 
            AND sucesso = FALSE
            AND data_tentativa > DATE_SUB(NOW(), INTERVAL 30 MINUTE)
        """
        result = db.fetch_one(query, (ip_address,))
        tentativas = result['tentativas'] if result else 0
        
        # Se atingiu o limite, bloqueia
        if tentativas >= Config.MAX_TENTATIVAS_LOGIN:
            expira_em = datetime.now() + timedelta(minutes=Config.TEMPO_BLOQUEIO_MINUTOS)
            
            # Verifica se já existe registro
            check = db.fetch_one(
                "SELECT id FROM ips_bloqueados WHERE ip_address = %s", 
                (ip_address,)
            )
            
            if check:
                query = """
                    UPDATE ips_bloqueados 
                    SET tentativas_falhas = tentativas_falhas + 1,
                        expira_em = %s,
                        ativo = TRUE
                    WHERE ip_address = %s
                """
                db.execute(query, (expira_em, ip_address))
            else:
                query = """
                    INSERT INTO ips_bloqueados 
                    (ip_address, tentativas_falhas, expira_em)
                    VALUES (%s, 1, %s)
                """
                db.execute(query, (ip_address, expira_em))
            
            return True  # IP foi bloqueado
        
        return False  # Ainda não bloqueado
    
    @staticmethod
    def processar_tentativa_sucesso(ip_address):
        """Processa uma tentativa bem-sucedida"""
        # Registra tentativa com sucesso
        IPBlocker.registrar_tentativa(ip_address, sucesso=True)
        
        # Se o IP estava bloqueado, desbloqueia
        db = Database()
        query = "UPDATE ips_bloqueados SET ativo = FALSE WHERE ip_address = %s"
        db.execute(query, (ip_address,))
    
    @staticmethod
    def listar_bloqueados():
        """Lista todos os IPs bloqueados (para admin)"""
        db = Database()
        query = """
            SELECT *, 
                   TIMESTAMPDIFF(MINUTE, NOW(), expira_em) as minutos_restantes
            FROM ips_bloqueados 
            WHERE ativo = TRUE AND expira_em > NOW()
            ORDER BY data_bloqueio DESC
        """
        return db.fetch_all(query)
    
    @staticmethod
    def desbloquear(ip_address):
        """Desbloqueia um IP manualmente"""
        db = Database()
        query = "UPDATE ips_bloqueados SET ativo = FALSE WHERE ip_address = %s"
        db.execute(query, (ip_address,))
        return True
    
    @staticmethod
    def estatisticas():
        """Estatísticas de bloqueios para admin"""
        db = Database()
        
        # Total de bloqueios ativos
        ativos = db.fetch_one("""
            SELECT COUNT(*) as total FROM ips_bloqueados 
            WHERE ativo = TRUE AND expira_em > NOW()
        """)
        
        # Bloqueios por motivo
        por_motivo = db.fetch_all("""
            SELECT motivo, COUNT(*) as total
            FROM ips_bloqueados
            WHERE data_bloqueio > DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY motivo
        """) or []
        
        # Tentativas nas últimas 24h
        tentativas = db.fetch_one("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN sucesso = TRUE THEN 1 ELSE 0 END) as sucessos,
                SUM(CASE WHEN sucesso = FALSE THEN 1 ELSE 0 END) as falhas
            FROM tentativas_login
            WHERE data_tentativa > DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """) or {'total': 0, 'sucessos': 0, 'falhas': 0}
        
        return {
            'ativos': ativos['total'] if ativos else 0,
            'por_motivo': por_motivo,
            'tentativas_24h': tentativas
        }