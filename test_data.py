# test_data.py
from models.contrato import Contrato
from models.usuario import Usuario

# Testar contratos da empresa 5
contratos = Contrato.listar_por_empresa(5)
print(f"Contratos empresa 5: {len(contratos)}")
for c in contratos:
    print(f"  {c.id}: {c.numero_contrato} - {c.status}")

# Testar usuários da empresa 5
usuarios = Usuario.listar_por_empresa(5)
print(f"Usuários empresa 5: {len(usuarios)}")
for u in usuarios:
    print(f"  {u.id}: {u.nome} - {u.perfil} - Ativo: {u.ativo}")