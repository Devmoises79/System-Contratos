"""
Gerenciamento de conexões com o banco de dados
"""
from config import Config
import mysql.connector
from mysql.connector import pooling
import logging

logger = logging.getLogger(__name__)

class DatabasePool:
    _pool = None
    _config = {
        'host': Config.MYSQL_HOST,
        'user': Config.MYSQL_USER,
        'password': Config.MYSQL_PASSWORD,
        'database': Config.MYSQL_DB,
        'port': Config.MYSQL_PORT,
        'pool_name': 'mypool',
        'pool_size': 10,
        'pool_reset_session': True,
        'autocommit': True,
        'ssl_disabled': True,  # 🔧 DESABILITAR SSL
        'use_pure': True
    }
    
    @classmethod
    def get_pool(cls):
        if cls._pool is None:
            try:
                cls._pool = mysql.connector.pooling.MySQLConnectionPool(**cls._config)
                logger.info("Pool de conexões criado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao criar pool: {e}")
                raise
        return cls._pool
    
    @classmethod
    def get_connection(cls):
        try:
            pool = cls.get_pool()
            return pool.get_connection()
        except Exception as e:
            logger.error(f"Erro ao obter conexão do pool: {e}")
            # Fallback para conexão normal (sem SSL)
            return mysql.connector.connect(
                host=Config.MYSQL_HOST,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DB,
                port=Config.MYSQL_PORT,
                autocommit=True,
                ssl_disabled=True,  # 🔧 DESABILITAR SSL
                use_pure=True
            )