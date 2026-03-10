# core/database.py
import mysql.connector
from mysql.connector import Error
from flask import g
from config import Config

class Database:
    """Gerenciador de conexão com o banco de dados"""
    
    def __init__(self):
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Estabelece conexão com o banco"""
        try:
            self.connection = mysql.connector.connect(
                host=Config.MYSQL_HOST,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DB,
                port=Config.MYSQL_PORT,
                autocommit=False
            )
            self.cursor = self.connection.cursor(dictionary=True)
            return True
        except Error as e:
            print(f"Erro ao conectar ao MySQL: {e}")
            return False
    
    def disconnect(self):
        """Fecha a conexão"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
        except Exception as e:
            print(f"Erro ao desconectar: {e}")
    
    def execute(self, query, params=None):
        """Executa uma query (INSERT, UPDATE, DELETE)"""
        try:
            if not self.connection or not self.connection.is_connected():
                if not self.connect():
                    return 0
            
            self.cursor.execute(query, params or ())
            self.connection.commit()
            return self.cursor.rowcount
        except Error as e:
            print(f"Erro ao executar query: {e}")
            if self.connection:
                self.connection.rollback()
            return 0
        except Exception as e:
            print(f"Erro inesperado: {e}")
            if self.connection:
                self.connection.rollback()
            return 0
    
    def execute_return_id(self, query, params=None):
        """Executa INSERT e retorna o ID inserido"""
        try:
            if not self.connection or not self.connection.is_connected():
                if not self.connect():
                    return None
            
            self.cursor.execute(query, params or ())
            self.connection.commit()
            return self.cursor.lastrowid
        except Error as e:
            print(f"Erro ao executar query: {e}")
            if self.connection:
                self.connection.rollback()
            return None
        except Exception as e:
            print(f"Erro inesperado: {e}")
            if self.connection:
                self.connection.rollback()
            return None
    
    def fetch_one(self, query, params=None):
        """Busca um único registro"""
        try:
            if not self.connection or not self.connection.is_connected():
                if not self.connect():
                    return None
            
            self.cursor.execute(query, params or ())
            return self.cursor.fetchone()
        except Error as e:
            print(f"Erro ao buscar dados: {e}")
            return None
    
    def fetch_all(self, query, params=None):
        """Busca múltiplos registros"""
        try:
            if not self.connection or not self.connection.is_connected():
                if not self.connect():
                    return []
            
            self.cursor.execute(query, params or ())
            return self.cursor.fetchall()
        except Error as e:
            print(f"Erro ao buscar dados: {e}")
            return []
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


# Função para obter conexão no Flask (usa g object)
def get_db():
    if 'db' not in g:
        g.db = Database()
        g.db.connect()
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.disconnect()