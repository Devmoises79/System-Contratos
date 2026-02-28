# core/utils.py
import re
import html
from datetime import datetime
import os
from werkzeug.utils import secure_filename

def sanitizar_entrada(texto):
    """Sanitiza entrada para evitar XSS"""
    if texto is None:
        return ""
    if isinstance(texto, str):
        return html.escape(texto.strip())
    return texto

def apenas_digitos(valor):
    """Remove tudo que não é dígito"""
    if valor is None:
        return ""
    return re.sub(r'\D', '', str(valor))

def validar_email(email):
    """Valida formato de email"""
    if not email:
        return False
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

def validar_senha_forte(senha):
    """Valida se a senha é forte"""
    if len(senha) < 8:
        return False, "A senha deve ter no mínimo 8 caracteres"
    if not re.search(r'[A-Z]', senha):
        return False, "A senha deve conter pelo menos uma letra maiúscula"
    if not re.search(r'[a-z]', senha):
        return False, "A senha deve conter pelo menos uma letra minúscula"
    if not re.search(r'[0-9]', senha):
        return False, "A senha deve conter pelo menos um número"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', senha):
        return False, "A senha deve conter pelo menos um caractere especial"
    return True, "Senha válida"

def formatar_cnpj(cnpj):
    """Formata CNPJ: 00.000.000/0001-00"""
    cnpj = apenas_digitos(cnpj)
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return cnpj

def validar_cnpj(cnpj):
    """Valida CNPJ (apenas dígitos)"""
    cnpj = apenas_digitos(cnpj)
    if len(cnpj) != 14:
        return False
    
    # Elimina CNPJs inválidos conhecidos
    if cnpj in [f"{i*14}" for i in range(10)]:
        return False
    
    return True

def formatar_telefone(telefone):
    """Formata telefone: (11) 99999-9999"""
    telefone = apenas_digitos(telefone)
    if len(telefone) == 11:
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
    elif len(telefone) == 10:
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
    return telefone

def formatar_valor(valor):
    """Formata valor monetário: R$ 1.234,56"""
    try:
        return f"R$ {float(valor):,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')
    except:
        return "R$ 0,00"

def gerar_nome_arquivo_seguro(nome_original):
    """Gera nome de arquivo seguro para upload"""
    import secrets
    
    nome, extensao = os.path.splitext(nome_original)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random = secrets.token_hex(4)
    
    nome_seguro = f"{timestamp}_{random}{extensao.lower()}"
    return secure_filename(nome_seguro)

def limitar_tamanho_texto(texto, limite=500):
    """Limita tamanho do texto"""
    if texto and len(texto) > limite:
        return texto[:limite]
    return texto