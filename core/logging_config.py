# core/logging_config.py
"""
Configuração de logging para a aplicação
"""
import logging
import sys
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Formatador de log com cores para terminal"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        record.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return super().format(record)


def setup_logging(app=None):
    """Configura o sistema de logging"""
    
    # Criar logger principal
    log = logging.getLogger()
    log.setLevel(logging.DEBUG if app and app.debug else logging.INFO)
    
    # Remover handlers existentes
    log.handlers.clear()
    
    # Handler para console com cores
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    console_format = ColoredFormatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    log.addHandler(console_handler)
    
    # Handler para arquivo
    file_handler = logging.FileHandler('logs/app.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    file_format = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] %(message)s'
    )
    file_handler.setFormatter(file_format)
    log.addHandler(file_handler)
    
    # Reduzir logs de bibliotecas externas
    logging.getLogger('mysql.connector').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    log.info("Sistema de logging configurado")
    
    return log


# Logger padrão para importação
logger = logging.getLogger(__name__)


class LoggingConfig:
    """Classe de configuração para compatibilidade"""
    @staticmethod
    def setup_logging(app=None):
        return setup_logging(app)
    
    @staticmethod
    def get_logger(name=None):
        if name:
            return logging.getLogger(name)
        return logger