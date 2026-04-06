"""
Configuração compartilhada para todos os testes
"""
import pytest
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def app():
    """Fixture para criar uma instância da aplicação Flask para testes"""
    from app import app as flask_app
    
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    
    yield flask_app


@pytest.fixture
def client(app):
    """Fixture para cliente de teste"""
    return app.test_client()


@pytest.fixture
def db_session():
    """Fixture para sessão do banco de dados (mock para testes)"""
    # Implementar mock do banco
    pass