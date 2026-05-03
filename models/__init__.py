# models/__init__.py
from models.empresa import Empresa
from models.usuario import Usuario
from models.contrato import Contrato
from models.notificacao import Notificacao
from models.gamificacao import Gamificacao, PontuacaoUsuario

__all__ = [
    'Empresa',
    'Usuario', 
    'Contrato',
    'Notificacao',
    'Gamificacao',
    'PontuacaoUsuario'
]