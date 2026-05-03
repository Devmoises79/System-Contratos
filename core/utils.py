# core/utils.py
"""
Funções utilitárias
"""
import re
import secrets
import string
import os
import hashlib
from datetime import datetime
from unidecode import unidecode


def sanitizar_entrada(texto):
    """Sanitiza uma string de entrada"""
    if not texto:
        return ''
    
    texto = texto.strip()
    texto = re.sub(r'<[^>]+>', '', texto)
    
    return texto


def apenas_digitos(texto):
    """Remove tudo que não é dígito de uma string"""
    if not texto:
        return ''
    
    return re.sub(r'[^0-9]', '', texto)


def validar_email(email):
    """Valida formato de e-mail"""
    if not email:
        return False
    
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None


def validar_cnpj(cnpj):
    """Valida CNPJ"""
    cnpj = apenas_digitos(cnpj)
    
    if len(cnpj) != 14:
        return False
    
    if cnpj in [str(i) * 14 for i in range(10)]:
        return False
    
    peso1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * peso1[i] for i in range(12))
    digito1 = 11 - (soma % 11)
    if digito1 >= 10:
        digito1 = 0
    
    if int(cnpj[12]) != digito1:
        return False
    
    peso2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * peso2[i] for i in range(13))
    digito2 = 11 - (soma % 11)
    if digito2 >= 10:
        digito2 = 0
    
    return int(cnpj[13]) == digito2


def validar_cpf(cpf):
    """Valida CPF"""
    cpf = apenas_digitos(cpf)
    
    if len(cpf) != 11:
        return False
    
    if cpf in [str(i) * 11 for i in range(10)]:
        return False
    
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = 11 - (soma % 11)
    if digito1 >= 10:
        digito1 = 0
    
    if int(cpf[9]) != digito1:
        return False
    
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = 11 - (soma % 11)
    if digito2 >= 10:
        digito2 = 0
    
    return int(cpf[10]) == digito2


def formatar_moeda(valor):
    """Formata valor para moeda brasileira"""
    if valor is None:
        return 'R$ 0,00'
    
    return f'R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def formatar_data(data, formato='%d/%m/%Y'):
    """Formata data para string"""
    if not data:
        return ''
    
    if isinstance(data, str):
        try:
            data = datetime.strptime(data, '%Y-%m-%d')
        except:
            return data
    
    return data.strftime(formato)


def gerar_token(tamanho=32):
    """Gera um token seguro aleatório"""
    return secrets.token_hex(tamanho)


def gerar_senha_aleatoria(tamanho=12):
    """Gera uma senha aleatória segura"""
    caracteres = string.ascii_letters + string.digits + "!@#$%*"
    return ''.join(secrets.choice(caracteres) for _ in range(tamanho))


def slugify(texto):
    """Converte texto para slug (URL amigável)"""
    if not texto:
        return ''
    
    texto = unidecode(texto.lower())
    texto = re.sub(r'[^a-z0-9]+', '-', texto)
    texto = texto.strip('-')
    
    return texto


def truncar_texto(texto, limite=100, sufixo='...'):
    """Trunca texto para um limite de caracteres"""
    if not texto:
        return ''
    
    if len(texto) <= limite:
        return texto
    
    return texto[:limite].strip() + sufixo


def gerar_nome_arquivo_seguro(nome_original, extensao=None):
    """
    Gera um nome de arquivo seguro e único
    
    Args:
        nome_original: Nome original do arquivo
        extensao: Extensão desejada (opcional)
    
    Returns:
        Nome seguro para o arquivo
    """
    if not nome_original:
        nome_original = 'arquivo'
    
    # Extrair extensão se não fornecida
    if extensao is None:
        if '.' in nome_original:
            extensao = nome_original.rsplit('.', 1)[-1].lower()
        else:
            extensao = ''
    
    # Criar slug do nome base
    nome_base = slugify(nome_original.rsplit('.', 1)[0] if '.' in nome_original else nome_original)
    
    # Limitar tamanho do nome base
    if len(nome_base) > 50:
        nome_base = nome_base[:50]
    
    # Adicionar timestamp e hash para garantir unicidade
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    hash_sufixo = secrets.token_hex(4)
    
    # Montar nome seguro
    if extensao:
        nome_seguro = f"{nome_base}_{timestamp}_{hash_sufixo}.{extensao}"
    else:
        nome_seguro = f"{nome_base}_{timestamp}_{hash_sufixo}"
    
    # Garantir que não há caracteres inválidos
    nome_seguro = re.sub(r'[^a-zA-Z0-9_.-]', '_', nome_seguro)
    
    return nome_seguro


def gerar_hash_arquivo(caminho_arquivo):
    """
    Gera hash MD5 de um arquivo
    
    Args:
        caminho_arquivo: Caminho do arquivo
    
    Returns:
        Hash MD5 do arquivo
    """
    hash_md5 = hashlib.md5()
    try:
        with open(caminho_arquivo, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        return None


def validar_extensao_arquivo(nome_arquivo, extensoes_permitidas):
    """
    Valida se a extensão do arquivo é permitida
    
    Args:
        nome_arquivo: Nome do arquivo
        extensoes_permitidas: Lista de extensões permitidas
    
    Returns:
        True se extensão é permitida, False caso contrário
    """
    if not nome_arquivo:
        return False
    
    if '.' not in nome_arquivo:
        return False
    
    extensao = nome_arquivo.rsplit('.', 1)[-1].lower()
    return extensao in extensoes_permitidas


def limpar_cnpj_cpf(texto):
    """Limpa CNPJ/CPF removendo formatação"""
    if not texto:
        return ''
    return re.sub(r'[^0-9]', '', texto)


def formatar_cnpj(cnpj):
    """Formata CNPJ para exibição"""
    cnpj = apenas_digitos(cnpj)
    if len(cnpj) != 14:
        return cnpj
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"


def formatar_cpf(cpf):
    """Formata CPF para exibição"""
    cpf = apenas_digitos(cpf)
    if len(cpf) != 11:
        return cpf
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:11]}"


def formatar_telefone(telefone):
    """Formata telefone para exibição"""
    telefone = apenas_digitos(telefone)
    
    if len(telefone) == 10:  # (XX) XXXX-XXXX
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:10]}"
    elif len(telefone) == 11:  # (XX) XXXXX-XXXX
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:11]}"
    else:
        return telefone


def formatar_cep(cep):
    """Formata CEP para exibição"""
    cep = apenas_digitos(cep)
    if len(cep) != 8:
        return cep
    return f"{cep[:5]}-{cep[5:8]}"


def calcular_idade(data_nascimento):
    """Calcula idade a partir da data de nascimento"""
    if not data_nascimento:
        return None
    
    if isinstance(data_nascimento, str):
        data_nascimento = datetime.strptime(data_nascimento, '%Y-%m-%d').date()
    
    hoje = datetime.now().date()
    idade = hoje.year - data_nascimento.year
    if hoje.month < data_nascimento.month or (hoje.month == data_nascimento.month and hoje.day < data_nascimento.day):
        idade -= 1
    
    return idade


def data_para_string(data, formato='%Y-%m-%d'):
    """Converte data para string no formato especificado"""
    if not data:
        return ''
    
    if isinstance(data, str):
        return data
    
    return data.strftime(formato)


def string_para_data(data_str, formato='%Y-%m-%d'):
    """Converte string para data"""
    if not data_str:
        return None
    
    try:
        return datetime.strptime(data_str, formato).date()
    except:
        return None