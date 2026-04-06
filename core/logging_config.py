"""
Sistema centralizado de logging para o System-Contratos
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Importação condicional do Flask para evitar circular imports
try:
    from flask import has_request_context, request, session
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    # Define classes dummy quando Flask não está disponível
    class DummyContext:
        def __getattr__(self, name):
            return ''
    has_request_context = lambda: False
    request = DummyContext()
    session = DummyContext()


class RequestFormatter(logging.Formatter):
    """Formatter que adiciona informações da requisição"""
    
    def format(self, record):
        if FLASK_AVAILABLE and has_request_context():
            try:
                record.url = request.url
                record.remote_addr = request.remote_addr
                record.method = request.method
                record.user_id = session.get('usuario', {}).get('id', 'anonymous')
            except:
                record.url = ''
                record.remote_addr = ''
                record.method = ''
                record.user_id = 'system'
        else:
            record.url = ''
            record.remote_addr = ''
            record.method = ''
            record.user_id = 'system'
        
        return super().format(record)


def setup_logging(app=None):
    """Configura o sistema de logging da aplicação"""
    
    # Cria diretório de logs se não existir
    log_dir = 'logs'
    try:
        os.makedirs(log_dir, exist_ok=True)
    except:
        pass
    
    # Configuração base
    log_format = '[%(asctime)s] [%(levelname)s] [User:%(user_id)s] [%(remote_addr)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Formatter com informações da requisição
    formatter = RequestFormatter(log_format, date_format)
    
    # Handler para arquivo principal (rotação)
    try:
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'system.log'),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
    except Exception as e:
        print(f"Erro ao criar file_handler: {e}")
        file_handler = None
    
    # Handler para erros (arquivo separado)
    try:
        error_handler = RotatingFileHandler(
            os.path.join(log_dir, 'error.log'),
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
            encoding='utf-8'
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
    except Exception as e:
        print(f"Erro ao criar error_handler: {e}")
        error_handler = None
    
    # Handler para segurança (logs de auth, IP blocker, etc)
    try:
        security_handler = RotatingFileHandler(
            os.path.join(log_dir, 'security.log'),
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
            encoding='utf-8'
        )
        security_handler.setFormatter(formatter)
        security_handler.setLevel(logging.WARNING)
    except Exception as e:
        print(f"Erro ao criar security_handler: {e}")
        security_handler = None
    
    # Configura o logger root
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    if file_handler:
        root_logger.addHandler(file_handler)
    if error_handler:
        root_logger.addHandler(error_handler)
    if security_handler:
        root_logger.addHandler(security_handler)
    
    # Se tiver app Flask, configura logging da aplicação
    if app:
        if file_handler:
            app.logger.addHandler(file_handler)
        if error_handler:
            app.logger.addHandler(error_handler)
        if security_handler:
            app.logger.addHandler(security_handler)
        
        # Configura logging de requisições HTTP
        if not app.debug:
            try:
                access_handler = RotatingFileHandler(
                    os.path.join(log_dir, 'access.log'),
                    maxBytes=10 * 1024 * 1024,
                    backupCount=5
                )
                access_handler.setLevel(logging.INFO)
                app.logger.addHandler(access_handler)
            except Exception as e:
                print(f"Erro ao criar access_handler: {e}")
    
    return root_logger


# Configura o logger básico (será sobrescrito quando o app Flask iniciar)
_logger = None

def get_logger():
    """Retorna o logger configurado (singleton pattern)"""
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger


class LoggerMixin:
    """Mixin para adicionar logging fácil às classes"""
    
    @property
    def logger(self):
        return get_logger()
    
    def log_info(self, message, **kwargs):
        self.logger.info(f"[{self.__class__.__name__}] {message}", extra=kwargs)
    
    def log_warning(self, message, **kwargs):
        self.logger.warning(f"[{self.__class__.__name__}] {message}", extra=kwargs)
    
    def log_error(self, message, **kwargs):
        self.logger.error(f"[{self.__class__.__name__}] {message}", extra=kwargs)
    
    def log_debug(self, message, **kwargs):
        self.logger.debug(f"[{self.__class__.__name__}] {message}", extra=kwargs)


# Exporta uma instância padrão do logger
logger = get_logger()