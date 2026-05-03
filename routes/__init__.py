# routes/__init__.py
from routes.contratos import contratos_bp
from routes.auth_routes import auth_bp
from routes.dashboard import dashboard_bp

__all__ = ['contratos_bp', 'auth_bp', 'dashboard_bp']