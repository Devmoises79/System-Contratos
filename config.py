# config.py
import os
from datetime import timedelta
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

class Config:
    # Chave secreta
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-mude-em-producao')
    
    # Banco de dados - AGORA USANDO validapy_db
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'Mo!ses@2004')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'validapy')  # Alterado para validapy_db
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    
    # Configurações de sessão
    SESSION_TIMEOUT = timedelta(hours=8)
    SESSION_TIMEOUT_LEMBRAR = timedelta(days=30)
    
    # Configurações de segurança
    MAX_TENTATIVAS_LOGIN = int(os.environ.get('MAX_TENTATIVAS_LOGIN', 5))
    TEMPO_BLOQUEIO_MINUTOS = int(os.environ.get('TEMPO_BLOQUEIO_MINUTOS', 30))
    
    # Uploads
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    
    # Perfis disponíveis
    PERFIS = ['admin_sistema', 'admin_empresa', 'gestor', 'assistente', 'analista']