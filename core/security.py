# core/security.py
import redis
import secrets
import re
import html
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from functools import wraps
from flask import request, session, abort, jsonify

# ============================================
# CONEXÃO COM MEMURAI (JÁ FUNCIONANDO!)
# ============================================

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True,
    socket_connect_timeout=5
)

# Testa conexão
redis_client.ping()  # Já sabemos que funciona!

# ============================================
# 1. PROTEÇÃO SQL INJECTION
# ============================================

class SQLInjectionProtection:
    @staticmethod
    def sanitize(value: str) -> str:
        """Remove padrões de SQL injection"""
        if not isinstance(value, str):
            return str(value) if value else ''
        
        # Remove caracteres perigosos
        dangerous = ["'", '"', "\\", ";", "--", "/*", "*/", "xp_", "sp_"]
        for char in dangerous:
            value = value.replace(char, '')
        
        # Remove comandos SQL comuns
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'UNION', 'ALTER']
        for keyword in sql_keywords:
            value = re.sub(r'(?i)' + keyword, '', value)
        
        return value.strip()

# ============================================
# 2. PROTEÇÃO XSS
# ============================================

class XSSProtection:
    @staticmethod
    def escape(text: str) -> str:
        """Escapa HTML para prevenir XSS"""
        return html.escape(str(text)) if text else ''
    
    @staticmethod
    def add_headers(response):
        """Adiciona headers de segurança"""
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        return response

# ============================================
# 3. PROTEÇÃO CSRF
# ============================================

class CSRFProtection:
    @staticmethod
    def generate_token(user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        redis_client.setex(f"csrf:{user_id}:{token}", 3600, '1')
        return token
    
    @staticmethod
    def validate_token(user_id: str, token: str) -> bool:
        if not token:
            return False
        return bool(redis_client.get(f"csrf:{user_id}:{token}"))
    
    @staticmethod
    def require_token(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if request.method in ['POST', 'PUT', 'DELETE']:
                token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
                user_id = session.get('user_id')
                if not user_id or not CSRFProtection.validate_token(str(user_id), token):
                    abort(403, "CSRF token inválido")
            return f(*args, **kwargs)
        return decorated

# ============================================
# 4. PROTEÇÃO FORÇA BRUTA
# ============================================

class BruteForceProtection:
    @staticmethod
    def check_login(email: str, ip: str) -> Tuple[bool, int]:
        """Verifica se pode tentar login"""
        key = f"bruteforce:login:{email}:{ip}"
        attempts = int(redis_client.get(key) or 0)
        
        if attempts >= 5:
            ttl = redis_client.ttl(key)
            return False, ttl if ttl > 0 else 900
        
        return True, 0
    
    @staticmethod
    def register_failed(email: str, ip: str):
        """Registra tentativa falha"""
        key = f"bruteforce:login:{email}:{ip}"
        attempts = redis_client.incr(key)
        if attempts == 1:
            redis_client.expire(key, 900)  # 15 minutos
    
    @staticmethod
    def reset_success(email: str, ip: str):
        """Reseta após login bem-sucedido"""
        redis_client.delete(f"bruteforce:login:{email}:{ip}")

# ============================================
# 5. PROTEÇÃO DDoS (RATE LIMITING)
# ============================================

class RateLimiter:
    @staticmethod
    def check(ip: str, endpoint: str, max_requests: int = 100, window: int = 60) -> Tuple[bool, int]:
        """Rate limiting por IP e endpoint"""
        key = f"ratelimit:{ip}:{endpoint}"
        current = int(redis_client.get(key) or 0)
        
        if current >= max_requests:
            ttl = redis_client.ttl(key)
            return False, ttl if ttl > 0 else window
        
        redis_client.incr(key)
        redis_client.expire(key, window)
        return True, 0

# ============================================
# MIDDLEWARE PRINCIPAL
# ============================================

def setup_security(app):
    """Configura todos os middlewares de segurança"""
    
    @app.before_request
    def before_request():
        # Sanitiza inputs (SQL Injection)
        if request.method in ['POST', 'PUT', 'PATCH']:
            if request.is_json:
                data = request.get_json()
                if data:
                    for key, value in data.items():
                        if isinstance(value, str):
                            data[key] = SQLInjectionProtection.sanitize(value)
            else:
                for key, value in request.form.items():
                    if isinstance(value, str):
                        request.form = request.form.copy()
                        request.form[key] = SQLInjectionProtection.sanitize(value)
        
        # Rate limiting (DDoS)
        ip = request.remote_addr
        endpoint = request.endpoint or 'unknown'
        limit_type = 'admin' if '/admin' in request.path else 'api'
        max_req = 30 if limit_type == 'admin' else 100
        
        can_proceed, wait = RateLimiter.check(ip, endpoint, max_req)
        if not can_proceed:
            abort(429, f"Muitas requisições. Aguarde {wait} segundos.")
    
    @app.after_request
    def after_request(response):
        # Headers de segurança (XSS)
        response = XSSProtection.add_headers(response)
        return response

# ============================================
# FUNÇÃO DE LOGIN SEGURO (EXEMPLO)
# ============================================

def login_seguro(email: str, senha: str, ip: str, verificar_senha_func) -> Dict[str, Any]:
    """Função genérica para login seguro"""
    
    # Sanitiza email
    email = SQLInjectionProtection.sanitize(email)
    
    # Verifica força bruta
    pode_tentar, tempo_restante = BruteForceProtection.check_login(email, ip)
    if not pode_tentar:
        return {
            'success': False,
            'error': f'Muitas tentativas. Aguarde {tempo_restante} segundos.'
        }
    
    # Verifica credenciais (usa sua função de verificação)
    user_id = verificar_senha_func(email, senha)
    
    if user_id:
        # Login bem-sucedido
        BruteForceProtection.reset_success(email, ip)
        
        # Gera tokens
        session['user_id'] = user_id
        session['session_token'] = secrets.token_urlsafe(32)
        
        csrf_token = CSRFProtection.generate_token(str(user_id))
        
        return {
            'success': True,
            'csrf_token': csrf_token,
            'user_id': user_id
        }
    else:
        # Login falhou
        BruteForceProtection.register_failed(email, ip)
        return {
            'success': False,
            'error': 'Email ou senha inválidos.'
        }