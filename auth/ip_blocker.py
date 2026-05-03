# auth/ip_blocker.py
"""
Sistema de bloqueio de IP para prevenir ataques de força bruta
"""
import time
from collections import defaultdict
from datetime import datetime, timedelta
import logging
from config import Config

logger = logging.getLogger(__name__)


class IPBlocker:
    """Gerenciador de bloqueio de IP para tentativas de login"""
    
    _attempts = defaultdict(list)
    _blocked_ips = {}
    
    @classmethod
    def _get_max_attempts(cls):
        return getattr(Config, 'MAX_TENTATIVAS_LOGIN', 5)
    
    @classmethod
    def _get_block_minutes(cls):
        return getattr(Config, 'TEMPO_BLOQUEIO_MINUTOS', 30)
    
    @classmethod
    def register_failed_attempt(cls, ip):
        """Registra uma tentativa de login falha"""
        if not ip:
            return
        
        now = time.time()
        cls._attempts[ip].append(now)
        
        # Limpa tentativas antigas (> 1 hora)
        one_hour_ago = now - 3600
        cls._attempts[ip] = [t for t in cls._attempts[ip] if t > one_hour_ago]
        
        total = len(cls._attempts[ip])
        max_attempts = cls._get_max_attempts()
        
        logger.warning(f"Tentativa falha para IP: {ip}. Total: {total}/{max_attempts}")
        
        # Verificar se deve bloquear
        if total >= max_attempts:
            block_until = datetime.now() + timedelta(minutes=cls._get_block_minutes())
            cls._blocked_ips[ip] = block_until
            logger.warning(f"IP {ip} BLOQUEADO até {block_until.strftime('%H:%M:%S')}")
    
    @classmethod
    def is_blocked(cls, ip):
        """Verifica se IP está bloqueado"""
        if not ip:
            return False
        
        # Verificar bloqueio ativo
        if ip in cls._blocked_ips:
            if datetime.now() < cls._blocked_ips[ip]:
                return True
            else:
                # Bloqueio expirado
                del cls._blocked_ips[ip]
        
        # Verificar tentativas no período
        now = time.time()
        attempts = cls._attempts.get(ip, [])
        block_seconds = cls._get_block_minutes() * 60
        
        recent = [t for t in attempts if now - t < block_seconds]
        
        return len(recent) >= cls._get_max_attempts()
    
    @classmethod
    def clear_failed_attempts(cls, ip):
        """Limpa tentativas falhas após login bem-sucedido"""
        if ip:
            if ip in cls._attempts:
                del cls._attempts[ip]
            if ip in cls._blocked_ips:
                del cls._blocked_ips[ip]
            logger.info(f"Tentativas limpas para IP: {ip}")
    
    @classmethod
    def get_block_time_remaining(cls, ip):
        """Retorna tempo restante de bloqueio em minutos"""
        if not ip:
            return 0
        
        if ip in cls._blocked_ips:
            remaining = (cls._blocked_ips[ip] - datetime.now()).total_seconds()
            return max(0, int(remaining / 60)) + 1
        
        return 0
    
    @classmethod
    def get_remaining_attempts(cls, ip):
        """Retorna o número de tentativas restantes"""
        if not ip or cls.is_blocked(ip):
            return 0
        
        recent = [t for t in cls._attempts.get(ip, []) 
                  if time.time() - t < cls._get_block_minutes() * 60]
        
        return max(0, cls._get_max_attempts() - len(recent))
    
    @classmethod
    def unblock_ip(cls, ip):
        """Desbloqueia um IP manualmente"""
        if ip in cls._blocked_ips:
            del cls._blocked_ips[ip]
            cls.clear_failed_attempts(ip)
            logger.info(f"IP {ip} desbloqueado manualmente")
            return True
        return False
    
    @classmethod
    def reset(cls):
        """Reseta todas as tentativas (para testes)"""
        cls._attempts.clear()
        cls._blocked_ips.clear()
        logger.info("IPBlocker resetado")


# Instância global para compatibilidade com chamadas de método de instância
ip_blocker = IPBlocker