# core/hash_utils.py
"""
Módulo de gerenciamento de hash de senhas - APENAS BCRYPT
Sem dependência do Werkzeug para hash
"""
import bcrypt
import logging

logger = logging.getLogger(__name__)


class HashUtils:
    """Gerenciador de hash de senhas usando apenas bcrypt"""
    
    @staticmethod
    def hash_senha(senha, rounds=12):
        """
        Gera um hash bcrypt para a senha
        
        Args:
            senha: Senha em texto plano
            rounds: Fator de custo (padrão 12)
        
        Returns:
            Hash bcrypt no formato $2b$XX$...
        """
        if not senha:
            logger.warning("Tentativa de hash com senha vazia")
            return ""
        
        try:
            # Gerar salt com o número de rounds especificado
            salt = bcrypt.gensalt(rounds=rounds)
            # Gerar o hash
            hash_senha = bcrypt.hashpw(senha.encode('utf-8'), salt)
            # Retornar como string
            resultado = hash_senha.decode('utf-8')
            
            logger.debug(f"Hash bcrypt gerado: {resultado[:30]}... (rounds={rounds})")
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao gerar hash bcrypt: {e}")
            return ""
    
    @staticmethod
    def verificar_senha(senha, hash_senha):
        """
        Verifica se a senha corresponde ao hash bcrypt
        
        Args:
            senha: Senha em texto plano
            hash_senha: Hash bcrypt armazenado
        
        Returns:
            True se a senha é válida, False caso contrário
        """
        if not senha:
            logger.warning("Senha vazia para verificação")
            return False
        
        if not hash_senha:
            logger.warning("Hash vazio para verificação")
            return False
        
        try:
            # Verificar se o hash tem formato bcrypt válido
            if not hash_senha.startswith('$2'):
                logger.warning(f"Hash não parece ser bcrypt: {hash_senha[:20]}...")
                return False
            
            # Verificar a senha
            resultado = bcrypt.checkpw(
                senha.encode('utf-8'),
                hash_senha.encode('utf-8')
            )
            
            if resultado:
                logger.debug("✅ Senha verificada com sucesso")
            else:
                logger.debug("❌ Senha inválida")
            
            return resultado
            
        except ValueError as e:
            logger.error(f"Erro de formato no bcrypt: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao verificar senha com bcrypt: {e}")
            return False
    
    @staticmethod
    def is_hash_valido(hash_senha):
        """
        Verifica se o hash tem formato bcrypt válido
        
        bcrypt tem formato: $2b$12$saltEhash (60 caracteres no total)
        """
        if not hash_senha:
            return False
        
        # Verificar formato bcrypt
        if not hash_senha.startswith('$2'):
            return False
        
        # Verificar tamanho (bcrypt tem 60 caracteres)
        if len(hash_senha) < 59 or len(hash_senha) > 61:
            logger.warning(f"Tamanho de hash inválido: {len(hash_senha)}")
            return False
        
        return True
    
    @staticmethod
    def get_hash_info(hash_senha):
        """Retorna informações sobre o hash bcrypt"""
        if not hash_senha:
            return {'valido': False, 'mensagem': 'Hash vazio'}
        
        if not hash_senha.startswith('$2'):
            return {'valido': False, 'mensagem': f'Não é bcrypt: {hash_senha[:10]}...'}
        
        # Extrair informações do hash
        partes = hash_senha.split('$')
        if len(partes) >= 3:
            versao = f"${partes[1]}$"
            rounds = partes[2][:2] if len(partes[2]) >= 2 else '?'
            return {
                'valido': True,
                'versao': versao,
                'rounds': rounds,
                'tamanho': len(hash_senha),
                'formato': f"bcrypt {versao} (2^{rounds} rounds)"
            }
        
        return {'valido': True, 'tamanho': len(hash_senha)}


# Instâncias globais
hash_manager = HashUtils()
hash_utils = HashUtils()


# Funções de conveniência
def gerar_hash_senha(senha):
    """Gera hash bcrypt para a senha"""
    return HashUtils.hash_senha(senha)


def verificar_senha(senha, hash_senha):
    """Verifica se a senha corresponde ao hash bcrypt"""
    return HashUtils.verificar_senha(senha, hash_senha)