# core/__init__.py
from core.database import Database, db, get_db, close_db, init_db
from core.hash_utils import HashUtils, hash_manager, hash_utils, gerar_hash_senha, verificar_senha
from core.logging_config import logger, setup_logging, LoggingConfig
from core.utils import (
    sanitizar_entrada,
    apenas_digitos,
    validar_email,
    validar_cnpj,
    validar_cpf,
    formatar_moeda,
    formatar_data,
    gerar_token,
    gerar_senha_aleatoria,
    slugify,
    truncar_texto
)

__all__ = [
    'Database',
    'db',
    'get_db',
    'close_db',
    'init_db',
    'HashUtils',
    'hash_manager',
    'hash_utils',
    'gerar_hash_senha',
    'verificar_senha',
    'logger',
    'setup_logging',
    'LoggingConfig',
    'sanitizar_entrada',
    'apenas_digitos',
    'validar_email',
    'validar_cnpj',
    'validar_cpf',
    'formatar_moeda',
    'formatar_data',
    'gerar_token',
    'gerar_senha_aleatoria',
    'slugify',
    'truncar_texto'
]