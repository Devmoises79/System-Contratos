# auth/__init__.py
from auth.login import auth_bp, login_manager, LoginManager
from auth.ip_blocker import IPBlocker, ip_blocker
from auth.permissoes import (
    login_required,
    permissao_required,
    admin_sistema_required,
    admin_empresa_required,
    gestor_required,
    analista_required,
    pode_criar_contrato,
    pode_editar_contrato,
    pode_aprovar_contrato,
    pode_analisar_contrato,
    pode_gerenciar_usuarios,
    pode_visualizar_relatorios,
    get_usuario_atual,
    get_usuario_id,
    get_empresa_id,
    get_perfil_usuario,
    is_admin_sistema,
    is_admin_empresa,
    is_gestor,
    is_analista
)

__all__ = [
    'auth_bp',
    'login_manager',
    'LoginManager',
    'IPBlocker',
    'ip_blocker',
    'login_required',
    'permissao_required',
    'admin_sistema_required',
    'admin_empresa_required',
    'gestor_required',
    'analista_required',
    'pode_criar_contrato',
    'pode_editar_contrato',
    'pode_aprovar_contrato',
    'pode_analisar_contrato',
    'pode_gerenciar_usuarios',
    'pode_visualizar_relatorios',
    'get_usuario_atual',
    'get_usuario_id',
    'get_empresa_id',
    'get_perfil_usuario',
    'is_admin_sistema',
    'is_admin_empresa',
    'is_gestor',
    'is_analista'
]