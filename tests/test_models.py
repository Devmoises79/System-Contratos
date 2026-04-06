"""
Testes unitários para os models do System-Contratos
Instalar: pip install pytest pytest-cov
Executar: pytest tests/ -v --cov=. --cov-report=html
"""
import pytest
import sys
import os
from datetime import datetime, timedelta

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.usuario import Usuario
from models.empresa import Empresa
from models.contrato import Contrato


class TestUsuario:
    """Testes para o modelo Usuario"""
    
    def test_criar_usuario(self):
        """Testa criação de usuário"""
        usuario = Usuario(
            nome="Test User",
            email="test@example.com",
            perfil="assistente"
        )
        
        assert usuario.nome == "Test User"
        assert usuario.email == "test@example.com"
        assert usuario.perfil == "assistente"
        assert usuario.ativo is True
    
    def test_definir_senha(self):
        """Testa definição de senha"""
        usuario = Usuario(email="test@example.com")
        resultado = usuario.definir_senha("SenhaForte123!")
        
        assert resultado is True
        assert usuario.senha_hash is not None
        assert usuario.senha_hash != "SenhaForte123!"
    
    def test_validar_forca_senha(self):
        """Testa validação de força da senha"""
        # Senha muito curta
        valido, msg = Usuario.validar_forca_senha("Abc12!")
        assert valido is False
        assert "mínimo 8 caracteres" in msg
        
        # Senha sem maiúscula
        valido, msg = Usuario.validar_forca_senha("abcdef123!")
        assert valido is False
        assert "maiúscula" in msg
        
        # Senha sem minúscula
        valido, msg = Usuario.validar_forca_senha("ABCDEF123!")
        assert valido is False
        assert "minúscula" in msg
        
        # Senha sem número
        valido, msg = Usuario.validar_forca_senha("Abcdefghi!")
        assert valido is False
        assert "número" in msg
        
        # Senha sem especial
        valido, msg = Usuario.validar_forca_senha("Abcdef123")
        assert valido is False
        assert "especial" in msg
        
        # Senha forte
        valido, msg = Usuario.validar_forca_senha("SenhaForte123!")
        assert valido is True
    
    def test_verificar_senha(self):
        """Testa verificação de senha"""
        usuario = Usuario(email="test@example.com")
        usuario.definir_senha("SenhaForte123!")
        
        assert usuario.verificar_senha("SenhaForte123!") is True
        assert usuario.verificar_senha("SenhaErrada") is False
    
    def test_gerar_token_recuperacao(self):
        """Testa geração de token de recuperação"""
        # Mock para evitar banco
        usuario = Usuario(email="test@example.com")
        usuario.id = 1  # Simula ID
        
        # Simula save sem banco
        def mock_save():
            pass
        usuario.save = mock_save
        
        token = usuario.gerar_token_recuperacao()
        
        assert token is not None
        assert len(token) > 20
        assert usuario.token_recuperacao == token
        assert usuario.token_expiracao > datetime.now()
    
    def test_perfil_display(self):
        """Testa exibição amigável do perfil"""
        usuario = Usuario(perfil="admin_sistema")
        assert usuario.get_perfil_display() == "Administrador do Sistema"
        
        usuario.perfil = "admin_empresa"
        assert usuario.get_perfil_display() == "Administrador da Empresa"
        
        usuario.perfil = "gestor"
        assert usuario.get_perfil_display() == "Gestor"
    
    def test_tem_permissao(self):
        """Testa verificação de permissões"""
        # Admin sistema tem todas permissões
        usuario_admin = Usuario(perfil="admin_sistema")
        assert usuario_admin.tem_permissao("qualquer_coisa") is True
        
        # Admin empresa tem permissões específicas
        usuario_admin_emp = Usuario(perfil="admin_empresa")
        assert usuario_admin_emp.tem_permissao("gerenciar_empresa") is True
        assert usuario_admin_emp.tem_permissao("gerenciar_usuarios") is True
        assert usuario_admin_emp.tem_permissao("permissao_invalida") is False
        
        # Assistente tem permissões limitadas
        usuario_assistente = Usuario(perfil="assistente")
        assert usuario_assistente.tem_permissao("criar_contratos") is True
        assert usuario_assistente.tem_permissao("editar_contratos") is True
        assert usuario_assistente.tem_permissao("aprovar_contratos") is False


class TestEmpresa:
    """Testes para o modelo Empresa"""
    
    def test_criar_empresa(self):
        """Testa criação de empresa"""
        empresa = Empresa(
            nome="Empresa Teste",
            cnpj="12345678000199",
            email="contato@empresa.com"
        )
        
        assert empresa.nome == "Empresa Teste"
        assert empresa.cnpj == "12345678000199"
        assert empresa.status == "trial"
    
    def test_cores_padrao(self):
        """Testa cores padrão da empresa"""
        empresa = Empresa(nome="Teste")
        
        assert "primaria" in empresa.paleta_cores
        assert "secundaria" in empresa.paleta_cores
        assert empresa.paleta_cores["primaria"] == "#2563eb"
    
    def test_status_validos(self):
        """Testa validação de status"""
        empresa = Empresa(nome="Teste", status="ativo")
        assert empresa.status == "ativo"
        
        empresa = Empresa(nome="Teste", status="invalido")
        assert empresa.status == "trial"  # Valor padrão
    
    def test_is_active(self):
        """Testa verificação de empresa ativa"""
        # Empresa ativa
        empresa_ativa = Empresa(nome="Ativa", status="ativo")
        assert empresa_ativa.is_active() is True
        
        # Empresa inativa
        empresa_inativa = Empresa(nome="Inativa", status="inativo")
        assert empresa_inativa.is_active() is False
        
        # Empresa trial sem expiração
        empresa_trial = Empresa(nome="Trial", status="trial")
        assert empresa_trial.is_active() is True  # Trial é considerado ativo


class TestContrato:
    """Testes para o modelo Contrato"""
    
    def test_criar_contrato(self):
        """Testa criação de contrato"""
        contrato = Contrato(
            empresa_id=1,
            contratante_nome="Empresa A",
            contratada_nome="Empresa B",
            valor=10000.00,
            descricao="Serviços de consultoria"
        )
        
        assert contrato.empresa_id == 1
        assert contrato.contratante_nome == "Empresa A"
        assert contrato.valor == 10000.00
        assert contrato.status == "rascunho"
    
    def test_gerar_numero_contrato(self):
        """Testa geração de número de contrato"""
        numero = Contrato.gerar_numero_contrato()
        
        assert numero.startswith("CT-")
        assert len(numero) > 10
        assert "-" in numero
    
    def test_fluxo_aprovacao(self):
        """Testa o fluxo de aprovação do contrato"""
        contrato = Contrato(
            empresa_id=1,
            contratante_nome="Empresa A",
            contratada_nome="Empresa B",
            valor=10000.00
        )
        
        # Mock para evitar banco
        contrato.id = 1
        
        # Status inicial
        assert contrato.status == "rascunho"
        
        # Envia para analista
        contrato.enviar_para_analista(1)
        assert contrato.status == "em_analise"
        
        # Envia para gestor
        contrato.enviar_para_gestor(1)
        assert contrato.status == "aguardando_aprovacao"
        assert contrato.solicitado_aprovacao is True
        
        # Aprova
        contrato.aprovar(1)
        assert contrato.status == "ativo"
        assert contrato.aprovado_por == 1
    
    def test_devolver_contrato(self):
        """Testa devolução de contrato"""
        contrato = Contrato(
            empresa_id=1,
            contratante_nome="Empresa A",
            contratada_nome="Empresa B",
            valor=10000.00
        )
        
        contrato.id = 1
        contrato.enviar_para_analista(1)
        contrato.enviar_para_gestor(1)
        
        # Devolve para analista
        motivo = "Revisar valores"
        contrato.devolver_para_analista(1, motivo)
        assert contrato.status == "em_analise"
        assert contrato.solicitado_aprovacao is False


class TestIntegracao:
    """Testes de integração (requerem banco de dados)"""
    
    @pytest.mark.skip(reason="Requer banco de dados configurado")
    def test_criar_usuario_com_empresa(self):
        """Testa criação de usuário vinculado a empresa"""
        # Este teste requer banco de dados real
        pass
    
    @pytest.mark.skip(reason="Requer banco de dados configurado")
    def test_buscar_contratos_por_empresa(self):
        """Testa busca de contratos por empresa"""
        pass


# Executar testes
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])