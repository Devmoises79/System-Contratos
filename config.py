# config.py
from datetime import timedelta

class Config:
    # Configurações do Banco de Dados
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'Mo!ses@2004'  # Coloque sua senha do MySQL aqui
    MYSQL_DB = 'validapy'
    MYSQL_PORT = 3306
    
    # Configurações do Flask
    SECRET_KEY = 'chave-secreta'
    
    # Configurações de Sessão
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # Sessão dura 2 horas
    
    # Configurações de Segurança
    MAX_TENTATIVAS_LOGIN = 5
    TEMPO_BLOQUEIO_MINUTOS = 30
    
    # Upload de arquivos
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
    UPLOAD_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'pdf']