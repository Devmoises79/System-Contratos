# admin/__init__.py
from admin.empresa import empresa_bp as admin_empresa_bp
from admin.sistema import sistema_bp as admin_sistema_bp

__all__ = ['admin_empresa_bp', 'admin_sistema_bp']